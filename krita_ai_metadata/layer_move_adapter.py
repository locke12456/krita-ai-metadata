from __future__ import annotations

from .ai_diffusion_compat import Layer, LayerManager, RestoreActiveLayer


class LayerMoveAdapter:
    def __init__(self, layer_manager: LayerManager) -> None:
        self.layer_manager = layer_manager

    def create_group_for_layer(self, layer: Layer, group_name: str) -> Layer:
        """Use krita-ai-diffusion's tested create_group_for() path."""
        if layer.is_root:
            raise ValueError("Cannot group root layer")
        group = self.layer_manager.create_group_for(layer)
        group.name = group_name
        group.refresh()
        self.layer_manager.update()
        return group

    def move_to_group(self, layer: Layer, group: Layer, above: Layer | None = None) -> Layer:
        """Move an additional layer into an already attached group."""
        if layer == group:
            raise ValueError("Cannot move a group into itself")
        if layer.is_root:
            raise ValueError("Cannot move root layer")
        old_parent = layer.parent_layer
        if old_parent is None:
            raise ValueError("Cannot move layer without parent")

        with RestoreActiveLayer(self.layer_manager):
            old_parent.node.removeChildNode(layer.node)
            group.node.addChildNode(layer.node, above.node if above else None)
            self.layer_manager.update()
            moved = self.layer_manager.wrap(layer.node)
            moved.refresh()
            group.refresh()
            return moved
