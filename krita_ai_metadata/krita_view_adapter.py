from __future__ import annotations

from typing import Any

from .krita_core_adapter import selected_krita_nodes


class KritaViewAdapter:
    """Adapter for Krita active-view selection access.

    The core export flow should not call Krita UI APIs directly. This adapter
    isolates active window, active view, and selected node access so scanner and
    UI code can depend on a small verified surface.
    """

    def active_view(self) -> Any | None:
        """Active view access is owned by krita_core_adapter.py."""
        return None

    def selected_nodes(self) -> list[Any]:
        """Return selected Krita node references from the core adapter."""
        return list(selected_krita_nodes())

    def selected_layers(self, layer_manager: Any) -> list[Any]:
        """Wrap selected Krita nodes as layer-manager objects when possible."""
        layers: list[Any] = []
        for node_ref in self.selected_nodes():
            if node_ref is None:
                continue
            raw_node = getattr(node_ref, "node", node_ref)
            try:
                layers.append(layer_manager.wrap(raw_node))
            except Exception:
                continue
        return layers

    def unique_selected_layers(self, layer_manager: Any) -> list[Any]:
        """Return selected layers without duplicate node IDs."""
        unique: list[Any] = []
        seen_ids: set[str] = set()

        for layer in self.selected_layers(layer_manager):
            layer_id = layer.id_string
            if layer_id in seen_ids:
                continue
            seen_ids.add(layer_id)
            unique.append(layer)

        return unique

    def has_selection(self) -> bool:
        """Return True when the active view has at least one selected node."""
        return len(self.selected_nodes()) > 0