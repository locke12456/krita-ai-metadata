from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .group_key import GroupKey, GroupKeyResolver
from .job_history_resolver import JobHistoryResolver
from .krita_core_adapter import create_group_for_nodes
from .layer_move_adapter import LayerMoveAdapter
from .sync_map_store import SyncRecord


@dataclass(slots=True)
class AutoMappingResult:
    """Result from a docker auto-mapping operation."""

    records: list[SyncRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def mapped_count(self) -> int:
        """Return the number of records written by this operation."""
        return len(self.records)


class AutoMappingService:
    """Headless layer-to-group metadata mapping service for the docker."""

    def __init__(
        self,
        layer_manager: Any,
        sync_map_store: Any,
        job_history_resolver: JobHistoryResolver | None = None,
        mover: LayerMoveAdapter | None = None,
        group_key_resolver: GroupKeyResolver | None = None,
    ) -> None:
        self.layer_manager = layer_manager
        self.sync_map_store = sync_map_store
        self.job_history_resolver = job_history_resolver or JobHistoryResolver()
        self.mover = mover or LayerMoveAdapter(layer_manager)
        self.group_key_resolver = group_key_resolver or GroupKeyResolver()

    def auto_map(self, layers: list[Any], manual_label: str = "") -> AutoMappingResult:
        """Create or repair group-backed sync records for selected layers."""
        return self.auto_map_with_ai_history(layers, manual_label=manual_label)

    def auto_map_with_ai_history(self, layers: list[Any], manual_label: str = "") -> AutoMappingResult:
        """Create or repair group-backed sync records using AI job history."""
        result = AutoMappingResult()
        label = manual_label.strip()

        if not label:
            result.warnings.append("Please enter a group label before auto mapping.")
            return result

        for layer in layers:
            record, warnings = self._map_one_layer(layer, label)
            result.warnings.extend(warnings)
            if record is not None:
                result.records.append(record)

        self.sync_map_store.load()
        self.layer_manager.update()
        return result

    def repair(self, layers: list[Any], manual_label: str = "") -> AutoMappingResult:
        """Repair selected layer mappings through the same verified headless path."""
        return self.auto_map(layers, manual_label=manual_label)

    def _map_one_layer(self, layer: Any, manual_label: str) -> tuple[SyncRecord | None, list[str]]:
        warnings: list[str] = []

        if layer.is_root:
            return None, [f"Skipped root layer '{layer.name}'."]

        existing_group_record = self.sync_map_store.resolve_group(
            group_id=layer.id_string,
            group_name=layer.name,
        )
        if existing_group_record is not None:
            return existing_group_record, []

        parent = layer.parent_layer
        parent_record = None
        if parent is not None:
            parent_record = self.sync_map_store.resolve_group(
                group_id=parent.id_string,
                group_name=parent.name,
            )

        source_record = self.sync_map_store.resolve_layer(layer.id_string)
        source_record_is_direct_layer = (
            source_record is not None and getattr(source_record, "target_type", "") == "layer"
        )
        source_record_is_stale_group = (
            source_record is not None and getattr(source_record, "target_type", "") == "group"
        )

        if parent_record is not None and source_record_is_direct_layer and parent_record is not source_record:
            return None, [
                f"Ambiguous metadata for layer '{layer.name}': layer record and parent group record both exist."
            ]

        if parent_record is not None:
            return parent_record, [
                f"Layer '{layer.name}' already inherits metadata from group '{parent.name}'."
            ]

        snapshot: dict[str, Any] = {}
        group_key: GroupKey | None = None

        if source_record_is_direct_layer:
            group_key = self._group_key_for_record(source_record, manual_label)
        else:
            if source_record_is_stale_group:
                warnings.append(f"Ignored stale group metadata for layer '{layer.name}'.")
            snapshot = self.job_history_resolver.params_snapshot_for_layers([layer])
            if snapshot:
                group_key = self._group_key_from_snapshot(snapshot, manual_label)

        if group_key is None:
            warnings.append(f"No metadata snapshot found for layer '{layer.name}'.")
            return None, warnings

        group = self.mover.create_group_for_layer(layer, group_key.group_name)
        self.layer_manager.update()
        group.refresh()

        if source_record_is_direct_layer:
            record = self._record_from_layer_record(layer, group, source_record, group_key)
            applied = self.sync_map_store.record_apply(record)
            self.sync_map_store.load()
            return applied, warnings

        record = self._record_from_snapshot(layer, group, snapshot, group_key)
        applied = self.sync_map_store.record_apply(record)
        self.sync_map_store.load()
        return applied, warnings

    def _record_from_layer_record(
        self,
        layer: Any,
        group: Any,
        source_record: SyncRecord,
        group_key: GroupKey,
    ) -> SyncRecord:
        """Convert a layer-backed sync record into a group-backed sync record."""
        return SyncRecord(
            target_type="group",
            export_key=group_key.key,
            layer_ids=[layer.id_string],
            job_id=source_record.job_id,
            image_index=source_record.image_index,
            seed=source_record.seed,
            params_snapshot=dict(source_record.params_snapshot),
            group_id=group.id_string,
            group_name=group_key.group_name,
            job_id_short=group_key.job_id_short,
            sync_index=group_key.sync_index,
            manual_label=group_key.manual_label,
        )

    def _record_from_snapshot(
        self,
        layer: Any,
        group: Any,
        snapshot: dict[str, Any],
        group_key: GroupKey,
    ) -> SyncRecord:
        """Create a new group-backed sync record from a job-history snapshot."""
        seed = int(snapshot.get("seed", 0) or 0)
        job_id = str(snapshot.get("job_id", "") or "")

        return SyncRecord(
            target_type="group",
            export_key=group_key.key,
            layer_ids=[layer.id_string],
            job_id=job_id,
            image_index=int(snapshot.get("image_index", 0) or 0),
            seed=seed,
            params_snapshot=dict(snapshot),
            group_id=group.id_string,
            group_name=group_key.group_name,
            job_id_short=group_key.job_id_short,
            sync_index=group_key.sync_index,
            manual_label=group_key.manual_label,
        )

    def _group_key_for_record(self, record: SyncRecord, manual_label: str) -> GroupKey:
        sync_index = record.sync_index if record.sync_index > 0 else self._next_sync_index()
        label = record.manual_label or manual_label
        return self.group_key_resolver.resolve(
            sync_index=sync_index,
            manual_label=label,
            image_index=record.image_index,
            job_id=record.job_id,
            seed=record.seed,
        )

    def _group_key_from_snapshot(self, snapshot: dict[str, Any], manual_label: str) -> GroupKey:
        return self.group_key_resolver.resolve(
            sync_index=self._next_sync_index(),
            manual_label=manual_label,
            image_index=int(snapshot.get("image_index", 0) or 0),
            job_id=str(snapshot.get("job_id", "") or ""),
            seed=int(snapshot.get("seed", 0) or 0),
        )

    def _next_sync_index(self) -> int:
        return self.sync_map_store.allocate_sync_index()

    def create_manual_group_record(self, layers: list[Any], manual_label: str = "") -> AutoMappingResult:
        """Create manual-only group sync records without reading job history snapshots."""
        result = AutoMappingResult()
        label = manual_label.strip()

        if not label:
            result.warnings.append("Please enter a group label before creating a manual group record.")
            return result

        for layer in layers:
            if getattr(layer, "is_root", False):
                result.warnings.append(f"Skipped root layer '{layer.name}'.")
                continue

            existing = self.sync_map_store.resolve_group(
                group_id=layer.id_string,
                group_name=layer.name,
            )
            if existing is not None:
                result.records.append(existing)
                continue

            sync_index = self._next_sync_index()
            group_key = self.group_key_resolver.resolve(
                sync_index=sync_index,
                manual_label=label,
                image_index=0,
                job_id="manual",
                seed=0,
            )
            group = self._create_manual_group(layer, group_key.group_name)
            self.layer_manager.update()
            group.refresh()

            record = SyncRecord(
                target_type="group",
                export_key=group_key.key,
                layer_ids=[layer.id_string],
                job_id="manual",
                image_index=0,
                seed=0,
                params_snapshot={},
                group_id=group.id_string,
                group_name=group_key.group_name,
                job_id_short="manual",
                sync_index=group_key.sync_index,
                manual_label=group_key.manual_label,
            )
            applied = self.sync_map_store.record_apply(record)
            self.sync_map_store.load()
            result.records.append(applied)

        self.sync_map_store.load()
        self.layer_manager.update()
        return result

    def _create_manual_group(self, layer: Any, group_name: str) -> Any:
        document_ref = getattr(layer, "document_ref", None)
        if document_ref is not None:
            return create_group_for_nodes(document_ref, [layer], group_name)
        return self.mover.create_group_for_layer(layer, group_name)

    def _fallback_export_key(self, layer: Any) -> str:
        raw = layer.name.strip() or layer.id_string
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in raw)
        return safe.strip("-") or layer.id_string.strip("{}")