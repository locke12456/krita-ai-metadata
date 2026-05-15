from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .group_key import GroupKeyResolver
from .job_history_resolver import JobHistoryResolver
from .layer_selection_model import LayerSelectionRow
from .sync_map_store import SyncMapStore, SyncRecord


@dataclass(slots=True)
class RemapMetadataRowResult:
    # Per-row outcome of the metadata-only re-map pipeline.
    layer_id: str
    name: str
    is_group: bool
    status: str  # "remapped" | "skipped" | "failed"
    reason: str
    record: SyncRecord | None = None


@dataclass(slots=True)
class RemapMetadataReport:
    # Aggregated report returned by RemapMetadataService.remap_for_rows.
    results: list[RemapMetadataRowResult] = field(default_factory=list)

    def remapped_count(self) -> int:
        return sum(1 for r in self.results if r.status == "remapped")

    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")

    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")


class RemapMetadataService:
    """Retry metadata mapping for unsynced rows.

    Invariants enforced by this service:
    - Never moves a Krita layer.
    - Never creates a Krita group node.
    - Never overwrites an existing SyncRecord.
    - Always emits a RemapMetadataRowResult per input row.
    - Failed / skipped rows always carry a non-empty reason.
    """

    def __init__(
        self,
        sync_map_store: SyncMapStore,
        job_history_resolver: JobHistoryResolver | None = None,
        group_key_resolver: GroupKeyResolver | None = None,
    ) -> None:
        self.sync_map_store = sync_map_store
        self.job_history_resolver = job_history_resolver or JobHistoryResolver()
        self.group_key_resolver = group_key_resolver or GroupKeyResolver()

    def remap_for_rows(
        self,
        rows: list[LayerSelectionRow],
        layer_lookup: dict[str, Any],
    ) -> RemapMetadataReport:
        # rows are pre-filtered by caller; layer_lookup maps layer_id -> krita layer.
        report = RemapMetadataReport()
        for row in rows:
            layer = layer_lookup.get(row.layer_id)
            report.results.append(self._remap_one(row, layer))
        return report

    def _remap_one(self, row: LayerSelectionRow, layer: Any) -> RemapMetadataRowResult:
        try:
            # 1. Layer must exist in the active document.
            if layer is None:
                return RemapMetadataRowResult(
                    layer_id=row.layer_id,
                    name=row.name,
                    is_group=row.is_group,
                    status="failed",
                    reason=f"Layer not found in document for id '{row.layer_id}'.",
                )

            # 2. Root layer is never re-mapped.
            if getattr(layer, "is_root", False):
                return RemapMetadataRowResult(
                    layer_id=row.layer_id,
                    name=row.name,
                    is_group=row.is_group,
                    status="skipped",
                    reason="Root layer is not eligible for re-map.",
                )

            # 3. Never overwrite an existing record.
            if row.is_group:
                existing = self.sync_map_store.resolve_group(
                    group_id=row.layer_id, group_name=row.name
                )
                if existing is not None:
                    return RemapMetadataRowResult(
                        layer_id=row.layer_id,
                        name=row.name,
                        is_group=True,
                        status="skipped",
                        reason=(
                            "Group already has a metadata record; "
                            "re-map only targets unsynced rows."
                        ),
                    )
            else:
                existing = self.sync_map_store.resolve_layer(row.layer_id)
                if existing is not None:
                    return RemapMetadataRowResult(
                        layer_id=row.layer_id,
                        name=row.name,
                        is_group=False,
                        status="skipped",
                        reason=(
                            "Layer already has a metadata record; "
                            "re-map only targets unsynced rows."
                        ),
                    )

            # 4. Retry metadata snapshot via job history (the only allowed retry).
            snapshot = self.job_history_resolver.params_snapshot_for_layers([layer])
            if not snapshot:
                return RemapMetadataRowResult(
                    layer_id=row.layer_id,
                    name=row.name,
                    is_group=row.is_group,
                    status="failed",
                    reason=f"No matching AI job history snapshot for layer '{row.name}'.",
                )

            job_id = str(snapshot.get("job_id", "") or "")
            image_index = int(snapshot.get("image_index", 0) or 0)
            seed = int(snapshot.get("seed", 0) or 0)
            sync_index = self.sync_map_store.allocate_sync_index()

            # 5. Build SyncRecord. Do NOT mutate Krita layer structure.
            if row.is_group:
                group_key = self.group_key_resolver.resolve_for_name(
                    sync_index=sync_index,
                    group_name=row.name,
                    job_id=job_id,
                    image_index=image_index,
                    seed=seed,
                )
                record = SyncRecord(
                    target_type="group",
                    export_key=group_key.key,
                    layer_ids=[row.layer_id],
                    job_id=job_id,
                    image_index=image_index,
                    seed=seed,
                    params_snapshot=dict(snapshot),
                    group_id=row.layer_id,
                    group_name=row.name,
                    job_id_short=group_key.job_id_short,
                    sync_index=sync_index,
                    manual_label=group_key.manual_label,
                )
            else:
                layer_name = str(getattr(layer, "name", "") or row.name or row.layer_id)
                record = SyncRecord(
                    target_type="layer",
                    export_key=self.group_key_resolver.sanitize(layer_name),
                    layer_ids=[row.layer_id],
                    job_id=job_id,
                    image_index=image_index,
                    seed=seed,
                    params_snapshot=dict(snapshot),
                    group_id=None,
                    group_name=None,
                    job_id_short=self.group_key_resolver.short_job_id(job_id),
                    sync_index=sync_index,
                    manual_label="",
                )

            # 6. Write through the existing store API.
            applied = self.sync_map_store.record_apply(record)
            return RemapMetadataRowResult(
                layer_id=row.layer_id,
                name=row.name,
                is_group=row.is_group,
                status="remapped",
                reason="",
                record=applied,
            )
        except Exception as exc:
            # Defensive: never let an exception bubble to the docker.
            return RemapMetadataRowResult(
                layer_id=row.layer_id,
                name=row.name,
                is_group=row.is_group,
                status="failed",
                reason=f"Unexpected error during re-map: {exc!r}",
            )