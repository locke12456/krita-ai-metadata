from __future__ import annotations

from ai_diffusion.layer import Layer, LayerManager, RestoreActiveLayer


class LayerMoveAdapter:
    def __init__(self, layer_manager: LayerManager) -> None:
        self.layer_manager = layer_manager

    def move_to_group(self, layer: Layer, group: Layer, above: Layer | None = None) -> Layer:
        if layer == group:
            raise ValueError("Cannot move a group into itself")
        old_parent = layer.parent_layer
        if old_parent is None:
            raise ValueError("Cannot move root layer")
        with RestoreActiveLayer(self.layer_manager):
            old_parent.node.removeChildNode(layer.node)
            group.node.addChildNode(layer.node, above.node if above else None)
            self.layer_manager.update()
            moved = self.layer_manager.wrap(layer.node)
            moved.refresh()
            return moved