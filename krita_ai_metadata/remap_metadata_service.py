from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from .group_key import GroupKeyResolver
from .job_history_resolver import JobHistoryResolver
from .layer_selection_model import LayerSelectionRow
from .sync_map_store import SyncMapStore, SyncRecord


def _log(msg):
    # Print to stderr so Krita's console shows it regardless of stdout buffering.
    print(f"[remap_metadata] {msg}", file=sys.stderr, flush=True)


@dataclass(slots=True)
class RemapMetadataRowResult:
    layer_id: str
    name: str
    is_group: bool
    status: str  # "remapped" | "skipped" | "failed"
    reason: str
    record: SyncRecord | None = None


@dataclass(slots=True)
class RemapMetadataReport:
    results: list[RemapMetadataRowResult] = field(default_factory=list)

    def remapped_count(self) -> int:
        return sum(1 for r in self.results if r.status == "remapped")

    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")

    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")


def is_manual_record(record):
    # Manual placeholders are written by AutoMappingService manual fallbacks.
    # Primary marker: job_id literal "manual". Secondary: empty params_snapshot.
    if record is None:
        return False
    if str(getattr(record, "job_id", "") or "").strip().lower() == "manual":
        return True
    if str(getattr(record, "job_id_short", "") or "").strip().lower() == "manual":
        return True
    snapshot = getattr(record, "params_snapshot", None) or {}
    if not snapshot:
        return True
    return False


class RemapMetadataService:
    """Retry metadata mapping for manual / unsynced rows.

    Invariants:
    - Never moves a Krita layer.
    - Never creates a Krita group node.
    - Never overwrites a record that already has real AI metadata.
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

    def existing_record_for(self, row: LayerSelectionRow):
        if row.is_group:
            return self.sync_map_store.resolve_group(
                group_id=row.layer_id, group_name=row.name
            )
        return self.sync_map_store.resolve_layer(row.layer_id)

    def remap_for_rows(
        self,
        rows: list[LayerSelectionRow],
        layer_lookup: dict[str, Any],
    ) -> RemapMetadataReport:
        _log(f"remap_for_rows: rows={len(rows)} lookup_size={len(layer_lookup)}")
        report = RemapMetadataReport()
        for row in rows:
            layer = layer_lookup.get(row.layer_id)
            result = self._remap_one(row, layer)
            _log(
                f"  -> {result.status:<8} name={row.name!r} "
                f"is_group={row.is_group} reason={result.reason!r}"
            )
            report.results.append(result)
        _log(
            f"remap_for_rows done: remapped={report.remapped_count()} "
            f"skipped={report.skipped_count()} failed={report.failed_count()}"
        )
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
                    reason=f"Layer not found in document for id {row.layer_id!r}.",
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

            # 3. Inspect existing record. Only manual / missing records may be
            #    re-mapped; real AI metadata is left untouched.
            existing = self.existing_record_for(row)
            if existing is not None and not is_manual_record(existing):
                snapshot_keys = ",".join(sorted((existing.params_snapshot or {}).keys()))
                return RemapMetadataRowResult(
                    layer_id=row.layer_id,
                    name=row.name,
                    is_group=row.is_group,
                    status="skipped",
                    reason=(
                        f"Row already has AI metadata "
                        f"(job_id={existing.job_id!r}, snapshot_keys=[{snapshot_keys}])."
                    ),
                    record=existing,
                )

            # 4. Retry metadata snapshot via job history.
            snapshot = self.job_history_resolver.params_snapshot_for_layers([layer])
            if not snapshot:
                return RemapMetadataRowResult(
                    layer_id=row.layer_id,
                    name=row.name,
                    is_group=row.is_group,
                    status="failed",
                    reason=(
                        f"No matching AI job history snapshot for layer {row.name!r} "
                        f"(existing_manual_record={existing is not None})."
                    ),
                )

            job_id = str(snapshot.get("job_id", "") or "")
            image_index = int(snapshot.get("image_index", 0) or 0)
            seed = int(snapshot.get("seed", 0) or 0)

            # Reuse the manual record's sync_index when overwriting so export keys stay stable.
            if existing is not None and existing.sync_index > 0:
                sync_index = existing.sync_index
            else:
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
                preserved_layer_ids = (
                    list(existing.layer_ids)
                    if existing is not None and existing.layer_ids
                    else [row.layer_id]
                )
                record = SyncRecord(
                    target_type="group",
                    export_key=group_key.key,
                    layer_ids=preserved_layer_ids,
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

            # 6. Write through the existing store API (overwrites the manual record).
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
            return RemapMetadataRowResult(
                layer_id=row.layer_id,
                name=row.name,
                is_group=row.is_group,
                status="failed",
                reason=f"Unexpected error during re-map: {exc!r}",
            )
