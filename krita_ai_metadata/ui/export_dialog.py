from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..export_manifest import ExportManifest
from ..export_policy import ExportDecision, ExportPolicy
from ..export_target_scanner import ExportMode, ExportTargetScanner
from ..group_composite_exporter import GroupCompositeExporter
from ..metadata_resolver import MetadataResolver
from ..png_sidecar_writer import ExportWriteResult, PngSidecarWriter


@dataclass(slots=True)
class ExportDialogConfig:
    """Configuration collected from the export UI."""

    output_dir: str | Path
    mode: ExportMode = ExportMode.selected
    overwrite: bool = False
    allow_unresolved: bool = False
    write_manifest: bool = True


@dataclass(slots=True)
class ExportReport:
    """User-facing batch export report."""

    results: list[ExportWriteResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    aborted: bool = False

    @property
    def exported_count(self) -> int:
        """Return the number of targets that wrote PNG files."""
        return sum(1 for result in self.results if result.png_path)

    @property
    def skipped_count(self) -> int:
        """Return the number of skipped targets."""
        return sum(1 for result in self.results if result.decision == ExportDecision.skip)


class ExportDialog:
    """Batch export coordinator for UI and command-style callers.

    This class intentionally keeps UI state separate from the export pipeline.
    A real Qt dialog can collect ExportDialogConfig, then call run() to execute
    the same scanner, resolver, render, and writer path used by probes.
    """

    def __init__(
        self,
        config: ExportDialogConfig,
        scanner: ExportTargetScanner | None = None,
        resolver: MetadataResolver | None = None,
        renderer: GroupCompositeExporter | None = None,
        writer: PngSidecarWriter | None = None,
        policy: ExportPolicy | None = None,
    ):
        self.config = config
        self.scanner = scanner or ExportTargetScanner()
        self.resolver = resolver or MetadataResolver()
        self.renderer = renderer or GroupCompositeExporter()
        self.writer = writer or PngSidecarWriter(overwrite=config.overwrite)
        self.policy = policy or ExportPolicy(
            allow_unresolved=config.allow_unresolved,
            default_decision=ExportDecision.export_without_metadata
            if config.allow_unresolved
            else ExportDecision.abort,
        )

    def run(self, layer_manager, sync_map_store) -> ExportReport:
        """Run batch export and return a report."""
        report = ExportReport()
        output_dir = Path(self.config.output_dir)
        manifest = ExportManifest() if self.config.write_manifest else None

        targets = self.scanner.scan(layer_manager, sync_map_store, self.config.mode)
        if not targets:
            report.warnings.append("No export targets found.")
            return report

        for target in targets:
            metadata = self.resolver.resolve(target)

            try:
                rendered = self.renderer.render(target)
                result = self.writer.write(output_dir, rendered, metadata, self.policy, manifest)
            except Exception as exc:
                warning = f"Failed to export '{target.key}': {exc}"
                report.warnings.append(warning)
                continue

            report.results.append(result)
            report.warnings.extend(result.warnings)

            if result.decision == ExportDecision.abort:
                report.aborted = True
                break

        if manifest is not None and not report.aborted:
            manifest.write(output_dir / "manifest.json")

        return report

    def resolved_preview(self, layer_manager, sync_map_store) -> list[dict]:
        """Return target preview rows for UI display."""
        rows: list[dict] = []
        targets = self.scanner.scan(layer_manager, sync_map_store, self.config.mode)

        for target in targets:
            metadata = self.resolver.resolve(target)
            rows.append(
                {
                    "key": target.key,
                    "layer_name": target.layer.name,
                    "target_type": target.target_type,
                    "resolved": metadata.has_metadata,
                    "warnings": metadata.warnings,
                }
            )

        return rows