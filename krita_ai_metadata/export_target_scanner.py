from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_diffusion.layer import Layer, LayerManager, LayerType

from .krita_view_adapter import KritaViewAdapter


class ExportMode(str, Enum):
    """Batch export target selection mode."""

    selected = "selected"
    visible = "visible"
    all = "all"


@dataclass(slots=True)
class ExportTarget:
    """Resolved layer or group export target."""

    layer: Layer
    target_type: str
    key: str
    record: dict[str, Any] | None
    warnings: list[str] = field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        """Return True when the target has a metadata sync record."""
        return self.record is not None


class ExportTargetScanner:
    """Build export targets from selected, visible, or all Krita layers."""

    def __init__(self, view_adapter: KritaViewAdapter | None = None):
        self._view_adapter = view_adapter or KritaViewAdapter()
        self.last_warnings: list[str] = []

    def scan(
        self,
        layer_manager: LayerManager,
        sync_map_store: Any,
        mode: ExportMode = ExportMode.selected,
        include_invisible_targets: bool = False,
    ) -> list[ExportTarget]:
        """Return export targets for the requested mode."""
        self.last_warnings = []
        targets: list[ExportTarget] = []

        for layer in self._candidate_layers(layer_manager, mode, include_invisible_targets):
            if not self._is_exportable_layer(layer):
                continue

            targets.append(self._target_from_layer(layer, sync_map_store))

        return targets

    def scan_selected_ids(
        self,
        layer_manager: LayerManager,
        sync_map_store: Any,
        selected_layer_ids: list[str],
        include_invisible_targets: bool = False,
    ) -> list[ExportTarget]:
        """Return export targets for explicit docker-selected layer IDs."""
        self.last_warnings = []
        selected = {layer_id for layer_id in selected_layer_ids if layer_id}
        targets: list[ExportTarget] = []

        for layer in layer_manager.all:
            if layer.id_string not in selected:
                continue

            warnings: list[str] = []
            if not layer.is_visible and not include_invisible_targets:
                warning = f"Hidden selected target '{layer.name}' was skipped."
                warnings.append(warning)
                self.last_warnings.append(warning)
                continue

            if not self._is_exportable_layer(layer):
                continue

            targets.append(self._target_from_layer(layer, sync_map_store, warnings))

        return targets

    def _candidate_layers(
        self,
        layer_manager: LayerManager,
        mode: ExportMode,
        include_invisible_targets: bool = False,
    ) -> list[Layer]:
        """Return candidate layers for one export mode."""
        if mode == ExportMode.selected:
            selected = self._view_adapter.unique_selected_layers(layer_manager)
            if selected:
                layers = selected
            else:
                layers = [layer_manager.active]
            if include_invisible_targets:
                return layers
            return [layer for layer in layers if layer.is_visible]

        layers = list(layer_manager.all)
        if mode == ExportMode.visible:
            return [layer for layer in layers if layer.is_visible]

        if include_invisible_targets:
            return layers

        return [layer for layer in layers if layer.is_visible]

    def _target_from_layer(
        self,
        layer: Layer,
        sync_map_store: Any,
        warnings: list[str] | None = None,
    ) -> ExportTarget:
        """Build one export target from a layer and sync-map store."""
        record, inherited_from = self._resolve_record(layer, sync_map_store)
        target_type = self._target_type(layer, record)
        key = self._target_key(layer, record)
        target_warnings = list(warnings or [])

        if inherited_from:
            target_warnings.append(
                f"Metadata for layer '{layer.name}' inherited from parent group '{inherited_from}'."
            )

        if record is None:
            target_warnings.append(f"No sync metadata found for layer '{layer.name}'.")

        return ExportTarget(
            layer=layer,
            target_type=target_type,
            key=key,
            record=record,
            warnings=target_warnings,
        )

    def _resolve_record(
        self,
        layer: Layer,
        sync_map_store: Any,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Resolve only metadata that is explicitly linked to this layer target."""
        layer_id = layer.id_string

        record = self._normalize_record(sync_map_store.resolve_layer(layer_id))
        if record is not None and self._record_applies_to_layer(record, layer_id):
            return record, None

        record = self._normalize_record(
            sync_map_store.resolve_group(group_id=layer_id, group_name=layer.name)
        )
        if record is not None:
            return record, None

        parent = layer.parent_layer
        if parent is not None:
            parent_record = self._normalize_record(
                sync_map_store.resolve_group(group_id=parent.id_string, group_name=parent.name)
            )
            if parent_record is not None and self._record_applies_to_layer(parent_record, layer_id):
                return parent_record, parent.name

        return None, None

    def _record_contains_layer(self, record: dict[str, Any], layer_id: str) -> bool:
        """Return True when a sync record explicitly references the layer id."""
        layer_ids = record.get("layer_ids", [])
        return isinstance(layer_ids, list) and layer_id in layer_ids

    def _record_applies_to_layer(self, record: dict[str, Any], layer_id: str) -> bool:
        """Return True when a record is compatible with a layer target."""
        layer_ids = record.get("layer_ids")
        if layer_ids is None:
            return True
        return isinstance(layer_ids, list) and layer_id in layer_ids

    def _is_exportable_layer(self, layer: Layer) -> bool:
        """Return True when the layer can be exported as image content."""
        return layer.type.is_image and not layer.bounds.is_zero

    def _target_type(self, layer: Layer, record: dict[str, Any] | None) -> str:
        """Return the effective target type."""
        if record is not None:
            value = record.get("target_type")
            if isinstance(value, str) and value:
                return value
        if layer.type == LayerType.group:
            return "group"
        return "layer"

    def _target_key(self, layer: Layer, record: dict[str, Any] | None) -> str:
        """Return export key from sync record or a safe fallback."""
        if record is not None:
            value = record.get("export_key") or record.get("key")
            if isinstance(value, str) and value:
                return value
        return self._fallback_key(layer)

    def _fallback_key(self, layer: Layer) -> str:
        """Build a deterministic fallback key for unresolved targets."""
        raw = layer.name.strip() or layer.id_string
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in raw)
        return safe.strip("-") or layer.id_string.strip("{}")

    def _call_optional(self, owner: Any, method_name: str, value: str) -> dict[str, Any] | None:
        """Call an optional resolver method when present."""
        method = getattr(owner, method_name, None)
        if method is None:
            return None

        try:
            result = method(value)
        except Exception:
            return None

        if isinstance(result, dict):
            return result

        if hasattr(result, "to_dict"):
            converted = result.to_dict()
            if isinstance(converted, dict):
                return converted

        return None

    def _lookup_map(self, owner: Any, attr_name: str, key: str) -> dict[str, Any] | None:
        """Read an optional record map by key, including SyncMapStore.data maps."""
        mapping = getattr(owner, attr_name, None)
        if not isinstance(mapping, dict):
            data = getattr(owner, "data", None)
            mapping = getattr(data, attr_name, None)

        if not isinstance(mapping, dict):
            return None

        return self._normalize_record(mapping.get(key))

    def _normalize_record(self, result: Any) -> dict[str, Any] | None:
        """Convert SyncRecord-like results into dictionaries."""
        if isinstance(result, dict):
            return dict(result)

        if hasattr(result, "to_dict"):
            converted = result.to_dict()
            if isinstance(converted, dict):
                return converted

        return None
