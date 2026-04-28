from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .capabilities import FeatureFlags, current_feature_flags
from .export_manifest import ExportManifest
from .export_options import ExportOptions
from .export_policy import ExportDecision, ExportPolicy
from .export_target_scanner import ExportMode, ExportTarget, ExportTargetScanner
from .group_composite_exporter import GroupCompositeExporter
from .metadata_resolver import MetadataResolver
from .png_sidecar_writer import ExportWriteResult, PngSidecarWriter


@dataclass(slots=True)
class DockerPreviewRow:
    """Read-only preview row for one export target."""

    key: str
    layer_name: str
    target_type: str
    resolved: bool
    inherited: bool
    output_path: str
    sidecar_path: str
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DockerPreviewReport:
    """Read-only docker preview report."""

    rows: list[DockerPreviewRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DockerExportReport:
    """Docker export execution report."""

    results: list[ExportWriteResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    aborted: bool = False

    @property
    def exported_count(self) -> int:
        """Return the number of written PNG files."""
        return sum(1 for result in self.results if result.png_path)

    @property
    def skipped_count(self) -> int:
        """Return the number of skipped targets."""
        return sum(1 for result in self.results if result.decision == ExportDecision.skip)


class DockerExportRunner:
    """Coordinate docker preview/export without owning UI state."""

    def __init__(
        self,
        scanner: ExportTargetScanner | None = None,
        resolver: MetadataResolver | None = None,
        renderer: GroupCompositeExporter | None = None,
        feature_flags: FeatureFlags | None = None,
    ) -> None:
        self.feature_flags = feature_flags or current_feature_flags()
        self.scanner = scanner or ExportTargetScanner()
        self.resolver = resolver or MetadataResolver(feature_flags=self.feature_flags)
        self.renderer = renderer or GroupCompositeExporter()

    def preview(
        self,
        layer_manager: Any,
        sync_map_store: Any,
        options: ExportOptions,
    ) -> DockerPreviewReport:
        """Build a read-only preview report."""
        self.feature_flags = current_feature_flags()
        if hasattr(self.resolver, "feature_flags"):
            self.resolver.feature_flags = self.feature_flags
        report = DockerPreviewReport(warnings=options.validate())
        targets = self._targets_for_options(layer_manager, sync_map_store, options)
        report.warnings.extend(getattr(self.scanner, "last_warnings", []))

        if not targets:
            report.warnings.append("No export targets found.")
            return report

        output_dir = Path(options.output_dir)
        for target in targets:
            metadata = self.resolver.resolve(target)
            output_path = output_dir / f"{metadata.key}.png"
            sidecar_path = output_path.with_suffix(".json")
            warnings = list(metadata.warnings)
            inherited = bool(metadata.payload.get("metadata_inherited", False))

            report.rows.append(
                DockerPreviewRow(
                    key=metadata.key,
                    layer_name=target.layer.name,
                    target_type=target.target_type,
                    resolved=metadata.has_metadata,
                    inherited=inherited,
                    output_path=str(output_path),
                    sidecar_path=str(sidecar_path),
                    warnings=warnings,
                )
            )

        return report

    def export(
        self,
        layer_manager: Any,
        sync_map_store: Any,
        options: ExportOptions,
    ) -> DockerExportReport:
        """Run docker export through the existing PNG writer pipeline."""
        self.feature_flags = current_feature_flags()
        if hasattr(self.resolver, "feature_flags"):
            self.resolver.feature_flags = self.feature_flags
        report = DockerExportReport(warnings=options.validate())
        if report.warnings:
            report.aborted = True
            return report

        output_dir = Path(options.output_dir)
        manifest = ExportManifest() if options.write_manifest else None
        policy = self._policy(options)
        writer = PngSidecarWriter(overwrite=options.overwrite)

        targets = self._targets_for_options(layer_manager, sync_map_store, options)
        report.warnings.extend(getattr(self.scanner, "last_warnings", []))
        if not targets:
            report.warnings.append("No export targets found.")
            return report

        for target in targets:
            metadata = self.resolver.resolve(target)

            try:
                rendered = self.renderer.render(target)
                result = writer.write(output_dir, rendered, metadata, policy, manifest)
            except Exception as exc:
                report.warnings.append(f"Failed to export '{target.key}': {exc}")
                continue

            report.results.append(result)
            report.warnings.extend(result.warnings)

            if result.decision == ExportDecision.abort:
                report.aborted = True
                break

        if manifest is not None and not report.aborted:
            manifest.write(output_dir / "manifest.json")

        return report

    def _targets_for_options(
        self,
        layer_manager: Any,
        sync_map_store: Any,
        options: ExportOptions,
    ) -> list[ExportTarget]:
        """Return export targets for docker options."""
        if options.mode == ExportMode.selected:
            return self.scanner.scan_selected_ids(
                layer_manager=layer_manager,
                sync_map_store=sync_map_store,
                selected_layer_ids=options.normalized_selected_layer_ids(),
                include_invisible_targets=options.include_invisible_targets,
            )

        return self.scanner.scan(layer_manager, sync_map_store, options.mode)

    def _policy(self, options: ExportOptions) -> ExportPolicy:
        """Build unresolved metadata policy for this run."""
        return ExportPolicy(
            allow_unresolved=options.allow_unresolved,
            default_decision=ExportDecision.export_without_metadata
            if options.allow_unresolved
            else ExportDecision.abort,
        )