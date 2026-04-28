from __future__ import annotations

from krita import Extension

from .qt_compat import QMessageBox


class KritaAIMetadataExtension(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        add_group_action = window.createAction(
            "krita_ai_metadata_add_group",
            "Add AI Metadata Group...",
            "tools/scripts",
        )
        add_group_action.triggered.connect(self.add_metadata_group)

        export_action = window.createAction(
            "krita_ai_metadata_export",
            "Export AI Metadata...",
            "tools/scripts",
        )
        export_action.triggered.connect(self.export_metadata)

        debug_action = window.createAction(
            "krita_ai_metadata_debug_probe",
            "AI Metadata Export Debug Probe",
            "tools/scripts",
        )
        debug_action.triggered.connect(self.debug_probe)

    def add_metadata_group(self):
        try:
            from .group_sync_action import MetadataGroupAction

            MetadataGroupAction().run_from_krita()
        except Exception as exc:
            self._show_error(f"Add group failed: {exc}")

    def export_metadata(self):
        try:
            from .export_action import ExportAction

            ExportAction().run_from_krita()
        except Exception as exc:
            self._show_error(f"Export failed: {exc}")

    def debug_probe(self):
        self._show_error("Krita AI Metadata Export plugin is loaded.")

    def _show_error(self, message: str):
        try:
            QMessageBox.warning(None, "Krita AI Metadata Export", message)
        except Exception:
            print(f"[krita_ai_metadata] {message}")
