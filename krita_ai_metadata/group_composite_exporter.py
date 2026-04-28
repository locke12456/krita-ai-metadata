from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .export_target_scanner import ExportTarget
from .krita_core_adapter import render_node_projection


@dataclass(slots=True)
class ExportedImage:
    """Rendered image payload for one export target."""

    image: Any
    bounds: Any
    source_layer_id: str
    source_layer_name: str


class GroupCompositeExporter:
    """Render a layer or group projection into an Image."""

    def render(self, target: ExportTarget) -> ExportedImage:
        """Render an export target."""
        return self.render_layer(target.layer)

    def render_layer(self, layer: Any) -> ExportedImage:
        """Render a layer or group using Krita projection pixels."""
        bounds = layer.bounds
        if bounds.is_zero:
            raise ValueError(f"Layer '{layer.name}' has empty bounds and cannot be exported.")

        if hasattr(layer, "get_pixels"):
            image = layer.get_pixels(bounds)
        else:
            image = render_node_projection(layer, bounds)
        return ExportedImage(
            image=image,
            bounds=bounds,
            source_layer_id=layer.id_string,
            source_layer_name=layer.name,
        )