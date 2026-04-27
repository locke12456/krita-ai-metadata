from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_diffusion.layer import Layer, LayerManager

from .job_history_resolver import JobHistoryResolver
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
        layer_manager: LayerManager,
        sync_map_store: Any,
        job_history_resolver: JobHistoryResolver | None = None,
        mover: LayerMoveAdapter | None = None,
    ) -> None:
        self.layer_manager = layer_manager
        self.sync_map_store = sync_map_store
        self.job_history_resolver = job_history_resolver or JobHistoryResolver()
        self.mover = mover or LayerMoveAdapter(layer_manager)

    def auto_map(self, layers: list[Layer]) -> AutoMappingResult:
        """Create or repair group-backed sync records for selected layers."""
        result = AutoMappingResult()

        for layer in layers:
            record, warnings = self._map_one_layer(layer)
            result.warnings.extend(warnings)
            if record is not None:
                result.records.append(record)

        self.sync_map_store.load()
        self.layer_manager.update()
        return result

    def repair(self, layers: list[Layer]) -> AutoMappingResult:
        """Repair selected layer mappings through the same verified headless path."""
        return self.auto_map(layers)

    def _map_one_layer(self, layer: Layer) -> tuple[SyncRecord | None, list[str]]:
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

        if parent_record is not None and source_record is not None and parent_record is not source_record:
            return None, [
                f"Ambiguous metadata for layer '{layer.name}': layer record and parent group record both exist."
            ]

        if parent_record is not None:
            return parent_record, [
                f"Layer '{layer.name}' already inherits metadata from group '{parent.name}'."
            ]

        group_name = f"{layer.name} Metadata Group"
        group = self.mover.create_group_for_layer(layer, group_name)
        self.layer_manager.update()
        group.refresh()

        if source_record is not None:
            record = self._record_from_layer_record(layer, group, source_record)
            applied = self.sync_map_store.record_apply(record)
            self.sync_map_store.load()
            return applied, warnings

        snapshot = self.job_history_resolver.params_snapshot_for_layers([layer])
        if snapshot:
            record = self._record_from_snapshot(layer, group, snapshot)
            applied = self.sync_map_store.record_apply(record)
            self.sync_map_store.load()
            return applied, warnings

        warnings.append(f"No metadata snapshot found for layer '{layer.name}'.")
        return None, warnings

    def _record_from_layer_record(
        self,
        layer: Layer,
        group: Layer,
        source_record: SyncRecord,
    ) -> SyncRecord:
        """Convert a layer-backed sync record into a group-backed sync record."""
        return SyncRecord(
            target_type="group",
            export_key=source_record.export_key,
            layer_ids=[layer.id_string],
            job_id=source_record.job_id,
            image_index=source_record.image_index,
            seed=source_record.seed,
            params_snapshot=dict(source_record.params_snapshot),
            group_id=group.id_string,
            group_name=group.name,
            job_id_short=source_record.job_id_short,
            sync_index=source_record.sync_index,
        )

    def _record_from_snapshot(
        self,
        layer: Layer,
        group: Layer,
        snapshot: dict[str, Any],
    ) -> SyncRecord:
        """Create a new group-backed sync record from a job-history snapshot."""
        seed = int(snapshot.get("seed", 0) or 0)
        job_id = str(snapshot.get("job_id", "") or "")

        return SyncRecord(
            target_type="group",
            export_key=self._fallback_export_key(layer),
            layer_ids=[layer.id_string],
            job_id=job_id,
            image_index=int(snapshot.get("image_index", 0) or 0),
            seed=seed,
            params_snapshot=dict(snapshot),
            group_id=group.id_string,
            group_name=group.name,
            job_id_short=job_id[:8],
            sync_index=0,
        )

    def _fallback_export_key(self, layer: Layer) -> str:
        raw = layer.name.strip() or layer.id_string
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in raw)
        return safe.strip("-") or layer.id_string.strip("{}")