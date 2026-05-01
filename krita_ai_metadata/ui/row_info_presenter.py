from __future__ import annotations

from dataclasses import dataclass
import re

from ..layer_selection_model import LayerSelectionRow


@dataclass(frozen=True, slots=True)
class ExportRowInfo:
    summary: str
    tooltip: str
    status_badge: str


class ExportRowInfoPresenter:
    """Format export layer rows into compact visible text and detailed tooltips."""

    def for_layer(self, row: LayerSelectionRow) -> ExportRowInfo:
        status_badge = self._status_badge(row)
        return ExportRowInfo(
            summary=self._summary(row),
            tooltip=self._tooltip(row),
            status_badge=status_badge,
        )

    def _summary(self, row: LayerSelectionRow) -> str:
        parts = [
            self._kind_icon(row),
            self._compact_state(row),
        ]

        display_name = self._display_name(row.name)
        if display_name.startswith("[Generated]"):
            parts.append(display_name)

        if not row.visible:
            parts.append("hidden")

        badge = self._status_badge(row)
        if badge:
            parts.append(badge)

        return " · ".join(part for part in parts if part)

    def _tooltip(self, row: LayerSelectionRow) -> str:
        lines = [
            self._line("Name", self._display_name(row.name)),
            self._line("Layer id", row.layer_id),
            self._line("Layer type", row.layer_type),
            self._line("Kind", "group" if row.is_group else "layer"),
            self._line("Visibility", "visible" if row.visible else "hidden"),
            self._line("Metadata state", row.metadata_state),
            self._line("Synced", self._yes_no(row.synced)),
            self._line("Inherited", self._yes_no(row.inherited)),
        ]

        if row.parent_group_id or row.parent_group_name:
            lines.append(self._line("Parent group id", row.parent_group_id))
            lines.append(self._line("Parent group name", row.parent_group_name))

        if row.synced:
            lines.append("State detail: this row has direct metadata sync.")
        elif row.inherited:
            lines.append("State detail: this row inherits metadata from its parent group.")
        else:
            lines.append("State detail: no metadata sync is resolved for this row.")

        return "\n".join(line for line in lines if line)

    def _status_badge(self, row: LayerSelectionRow) -> str:
        if not row.visible:
            return "🙈"
        if row.inherited:
            return "↳"
        if row.synced:
            return "✓"
        return "⚠"

    def _compact_state(self, row: LayerSelectionRow) -> str:
        state = self._safe_text(row.metadata_state, "unknown")
        if row.is_group:
            return f"group {state}"
        return f"layer {state}"

    def _kind_icon(self, row: LayerSelectionRow) -> str:
        return "📁" if row.is_group else "🖼"

    def _line(self, label: str, value: object) -> str:
        return f"{label}: {self._safe_text(value)}"

    def _display_name(self, value: object) -> str:
        raw = self._safe_text(value, "unknown")
        if not raw.startswith("[Generated"):
            return raw
        short_name, seed_number = self._generated_name_parts(raw)
        if seed_number:
            return f"[Generated] {short_name} ({seed_number})"
        return f"[Generated] {short_name}"

    def _generated_name_parts(self, value: str) -> tuple[str, str]:
        raw = str(value or "").strip()
        seed_match = re.search(r"\((\d+)\)\s*$", raw)
        seed_number = seed_match.group(1) if seed_match else ""
        if seed_match:
            raw = raw[:seed_match.start()].strip()

        raw = re.sub(r"^\[Generated[^\]]*\]\s*", "", raw).strip()
        raw = re.sub(r"\s+", " ", raw).strip(" -_")
        if not raw:
            raw = "generated"

        max_chars = 36
        if len(raw) > max_chars:
            raw = raw[:max_chars].rstrip(" -_") + "..."
        return raw, seed_number

    def _yes_no(self, value: bool) -> str:
        return "yes" if value else "no"

    def _safe_text(self, value: object, fallback: str = "unknown") -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text if text else fallback