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

    def scan(
        self,
        layer_manager: LayerManager,
        sync_map_store: Any,
        mode: ExportMode = ExportMode.selected,
    ) -> list[ExportTarget]:
        """Return export targets for the requested mode."""
        targets: list[ExportTarget] = []

        for layer in self._candidate_layers(layer_manager, mode):
            if not self._is_exportable_layer(layer):
                continue

            record = self._resolve_record(layer, sync_map_store)
            target_type = self._target_type(layer, record)
            key = self._target_key(layer, record)
            warnings: list[str] = []

            if record is None:
                warnings.append(f"No sync metadata found for layer '{layer.name}'.")

            targets.append(
                ExportTarget(
                    layer=layer,
                    target_type=target_type,
                    key=key,
                    record=record,
                    warnings=warnings,
                )
            )

        return targets

    def _candidate_layers(self, layer_manager: LayerManager, mode: ExportMode) -> list[Layer]:
        """Return candidate layers for one export mode."""
        if mode == ExportMode.selected:
            selected = self._view_adapter.unique_selected_layers(layer_manager)
            if selected:
                return selected
            return [layer_manager.active]

        layers = list(layer_manager.all)
        if mode == ExportMode.visible:
            return [layer for layer in layers if layer.is_visible]

        return layers

    def _resolve_record(self, layer: Layer, sync_map_store: Any) -> dict[str, Any] | None:
        """Resolve sync metadata by layer ID, group ID, then group name."""
        layer_id = layer.id_string

        record = self._call_optional(sync_map_store, "resolve_layer", layer_id)
        if record is not None:
            return record

        record = self._call_optional(sync_map_store, "resolve_group_id", layer_id)
        if record is not None:
            return record

        record = self._call_optional(sync_map_store, "resolve_group_name", layer.name)
        if record is not None:
            return record

        record = self._lookup_map(sync_map_store, "records_by_layer_id", layer_id)
        if record is not None:
            return record

        record = self._lookup_map(sync_map_store, "records_by_group_id", layer_id)
        if record is not None:
            return record

        record = self._lookup_map(sync_map_store, "records_by_group_name", layer.name)
        if record is not None:
            return record

        parent = layer.parent_layer
        if parent is not None:
            parent_record = self._lookup_map(sync_map_store, "records_by_group_id", parent.id_string)
            if parent_record is not None:
                return parent_record
            return self._lookup_map(sync_map_store, "records_by_group_name", parent.name)

        return None

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
