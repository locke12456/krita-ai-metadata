from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExportManifestEntry:
    """One batch export manifest entry."""

    version: int
    key: str
    target_type: str
    png_path: str | None
    json_path: str | None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable manifest entry."""
        return {
            "version": self.version,
            "key": self.key,
            "target_type": self.target_type,
            "png_path": self.png_path,
            "json_path": self.json_path,
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ExportManifest:
    """Batch export manifest writer."""

    entries: list[ExportManifestEntry] = field(default_factory=list)

    def add_entry(self, entry: ExportManifestEntry) -> None:
        """Append one export manifest entry."""
        self.entries.append(entry)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable batch manifest."""
        return {
            "version": 1,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def write(self, filepath: str | Path) -> None:
        """Write manifest.json to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        path.write_text(payload, encoding="utf-8")