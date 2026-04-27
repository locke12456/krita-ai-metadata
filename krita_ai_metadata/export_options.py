from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .export_target_scanner import ExportMode
from .ui.export_dialog import ExportDialogConfig


@dataclass(slots=True)
class ExportOptions:
    """Normalized docker export options for the PNG-only v1.1 export path."""

    output_dir: str | Path
    mode: ExportMode = ExportMode.selected
    selected_layer_ids: list[str] = field(default_factory=list)
    overwrite: bool = False
    allow_unresolved: bool = False
    write_manifest: bool = True
    include_invisible_targets: bool = False
    image_extension: str = "png"

    def validate(self) -> list[str]:
        """Return validation warnings for unsupported executable options."""
        warnings: list[str] = []

        if not self.output_dir:
            warnings.append("Output directory is required.")

        extension = self.image_extension.lower().lstrip(".")
        if extension != "png":
            warnings.append("Only PNG export is supported in v1.1.")

        if self.mode == ExportMode.selected and not self.selected_layer_ids:
            warnings.append("No docker layer selection is set.")

        return warnings

    def to_dialog_config(self) -> ExportDialogConfig:
        """Map fallback-compatible fields to the existing Tools/Scripts config."""
        return ExportDialogConfig(
            output_dir=self.output_dir,
            mode=self.mode,
            overwrite=self.overwrite,
            allow_unresolved=self.allow_unresolved,
            write_manifest=self.write_manifest,
        )

    def normalized_selected_layer_ids(self) -> list[str]:
        """Return stable selected layer ids without duplicates or empty values."""
        result: list[str] = []
        seen: set[str] = set()

        for layer_id in self.selected_layer_ids:
            if not layer_id or layer_id in seen:
                continue
            seen.add(layer_id)
            result.append(layer_id)

        return result