from __future__ import annotations

from typing import Any

import krita

from ai_diffusion.layer import Layer, LayerManager


class KritaViewAdapter:
    """Adapter for Krita active-view selection access.

    The core export flow should not call Krita UI APIs directly. This adapter
    isolates active window, active view, and selected node access so scanner and
    UI code can depend on a small verified surface.
    """

    def active_view(self) -> Any | None:
        """Return the current Krita active view, or None when unavailable."""
        app = krita.Krita.instance()
        if app is None:
            return None

        window = app.activeWindow()
        if window is None:
            return None

        view = window.activeView()
        if view is None:
            return None

        return view

    def selected_nodes(self) -> list[Any]:
        """Return selected Krita nodes from the active view."""
        view = self.active_view()
        if view is None:
            return []

        nodes = view.selectedNodes()
        if nodes is None:
            return []

        return list(nodes)

    def selected_layers(self, layer_manager: LayerManager) -> list[Layer]:
        """Wrap selected Krita nodes as Layer objects."""
        layers: list[Layer] = []
        for node in self.selected_nodes():
            if node is None:
                continue
            try:
                layers.append(layer_manager.wrap(node))
            except Exception:
                continue
        return layers

    def unique_selected_layers(self, layer_manager: LayerManager) -> list[Layer]:
        """Return selected layers without duplicate node IDs."""
        unique: list[Layer] = []
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