from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ExportDecision(str, Enum):
    """Decision for an export target that cannot be resolved to metadata."""

    skip = "skip"
    export_without_metadata = "export_without_metadata"
    abort = "abort"


@dataclass(slots=True)
class ExportPolicy:
    """Policy surface for unresolved export targets.

    The exporter must not silently inject unrelated metadata. Every unresolved
    target is routed through this object so CLI, probe, and UI flows use the
    same decision model.
    """

    allow_unresolved: bool = False
    default_decision: ExportDecision = ExportDecision.skip

    def on_unresolved_target(self, target: Any, warning: str) -> ExportDecision:
        """Return the decision for an unresolved target."""
        if not self.allow_unresolved:
            return ExportDecision.abort

        if self.default_decision == ExportDecision.abort:
            return ExportDecision.abort

        if self.default_decision == ExportDecision.export_without_metadata:
            return ExportDecision.export_without_metadata

        return ExportDecision.skip

    @staticmethod
    def should_write_without_metadata(decision: ExportDecision) -> bool:
        """Return True when export should continue without metadata."""
        return decision == ExportDecision.export_without_metadata

    @staticmethod
    def should_skip(decision: ExportDecision) -> bool:
        """Return True when the target should be skipped."""
        return decision == ExportDecision.skip

    @staticmethod
    def should_abort(decision: ExportDecision) -> bool:
        """Return True when the batch should abort."""
        return decision == ExportDecision.abort