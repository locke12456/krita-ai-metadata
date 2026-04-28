from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .export_manifest import ExportManifest, ExportManifestEntry
from .export_policy import ExportDecision, ExportPolicy
from .group_composite_exporter import ExportedImage
from .metadata_resolver import ResolvedMetadata


@dataclass(slots=True)
class ExportWriteResult:
    """File write result for one export target."""

    key: str
    png_path: str | None
    json_path: str | None
    decision: ExportDecision | None
    warnings: list[str] = field(default_factory=list)


class PngSidecarWriter:
    """Write PNG metadata, JSON sidecars, and optional manifest entries."""

    def __init__(self, overwrite: bool = False):
        self.overwrite = overwrite

    def write(
        self,
        output_dir: str | Path,
        rendered: ExportedImage,
        metadata: ResolvedMetadata,
        policy: ExportPolicy,
        manifest: ExportManifest | None = None,
    ) -> ExportWriteResult:
        """Write one rendered target to PNG and sidecar JSON."""
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)

        warnings = list(metadata.warnings)
        decision: ExportDecision | None = None

        manual_mode = metadata.payload.get("mode") == "manual_only"
        if not metadata.has_metadata and not manual_mode:
            warning = f"No metadata available for '{metadata.key}'."
            if warning not in warnings:
                warnings.append(warning)
            decision = policy.on_unresolved_target(metadata.target, warning)

            if policy.should_abort(decision):
                return ExportWriteResult(metadata.key, None, None, decision, warnings)

            if policy.should_skip(decision):
                return ExportWriteResult(metadata.key, None, None, decision, warnings)

        png_path = self._next_available_path(directory / f"{metadata.key}.png", self.overwrite)
        json_path = png_path.with_suffix(".json")

        if metadata.has_metadata:
            rendered.image.save_png_with_metadata(png_path, metadata.a1111_parameters)
        else:
            rendered.image.save(png_path)

        payload = dict(metadata.payload)
        payload["warnings"] = warnings
        payload["png_path"] = str(png_path)
        payload["json_path"] = str(json_path)
        payload["source_layer_id"] = rendered.source_layer_id
        payload["source_layer_name"] = rendered.source_layer_name
        payload["bounds"] = [
            rendered.bounds.x,
            rendered.bounds.y,
            rendered.bounds.width,
            rendered.bounds.height,
        ]

        self._write_json(json_path, payload)

        result = ExportWriteResult(
            key=metadata.key,
            png_path=str(png_path),
            json_path=str(json_path),
            decision=decision,
            warnings=warnings,
        )

        if manifest is not None:
            manifest.add_entry(
                ExportManifestEntry(
                    version=1,
                    key=metadata.key,
                    target_type=metadata.payload.get("target_type", metadata.target.target_type),
                    png_path=result.png_path,
                    json_path=result.json_path,
                    warnings=warnings,
                    metadata={
                        "job_id": metadata.payload.get("job_id", ""),
                        "image_index": metadata.payload.get("image_index", 0),
                        "seed": metadata.payload.get("seed", 0),
                    },
                )
            )

        return result

    def _next_available_path(self, path: Path, overwrite: bool) -> Path:
        """Return an available path, adding a numeric suffix when needed."""
        if overwrite or not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        index = 1

        while True:
            candidate = parent / f"{stem}-{index:03d}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    def _write_json(self, path: Path, payload: dict) -> None:
        """Write a UTF-8 JSON sidecar file."""
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        path.write_text(text, encoding="utf-8")