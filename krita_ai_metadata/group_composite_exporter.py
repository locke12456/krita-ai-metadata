from __future__ import annotations

from dataclasses import dataclass

from ai_diffusion.image import Bounds, Image
from ai_diffusion.layer import Layer

from .export_target_scanner import ExportTarget


@dataclass(slots=True)
class ExportedImage:
    """Rendered image payload for one export target."""

    image: Image
    bounds: Bounds
    source_layer_id: str
    source_layer_name: str


class GroupCompositeExporter:
    """Render a layer or group projection into an Image."""

    def render(self, target: ExportTarget) -> ExportedImage:
        """Render an export target."""
        return self.render_layer(target.layer)

    def render_layer(self, layer: Layer) -> ExportedImage:
        """Render a layer or group using Krita projection pixels."""
        bounds = layer.bounds
        if bounds.is_zero:
            raise ValueError(f"Layer '{layer.name}' has empty bounds and cannot be exported.")

        image = layer.get_pixels(bounds)
        return ExportedImage(
            image=image,
            bounds=bounds,
            source_layer_id=layer.id_string,
            source_layer_name=layer.name,
        )