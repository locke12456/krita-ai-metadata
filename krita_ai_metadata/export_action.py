from __future__ import annotations

from pathlib import Path
from typing import Any

from .ai_diffusion_compat import active_document
from .export_target_scanner import ExportMode
from .qt_compat import QFileDialog, QMessageBox
from .job_history_resolver import JobHistoryResolver
from .sync_map_store import SyncMapStore
from .ui.export_dialog import ExportDialog, ExportDialogConfig


class ExportAction:
    def run_from_krita(self) -> None:
        document = active_document()
        if document is None:
            QMessageBox.warning(None, "Krita AI Metadata Export", "No active Krita document.")
            return

        ok, message = document.check_color_mode()
        if not ok:
            QMessageBox.warning(None, "Krita AI Metadata Export", message or "Document is not compatible.")
            return

        output_dir = QFileDialog.getExistingDirectory(
            None,
            "Select AI metadata export folder",
            self._default_output_dir(document),
        )
        if not output_dir:
            return

        store = SyncMapStore(document)
        self._repair_empty_selected_records(document, store)

        config = ExportDialogConfig(
            output_dir=Path(output_dir),
            mode=ExportMode.selected,
            overwrite=False,
            allow_unresolved=False,
            write_manifest=True,
        )
        report = ExportDialog(config).run(document.layers, store)

        if report.exported_count <= 0:
            QMessageBox.warning(
                None,
                "Krita AI Metadata Export",
                "No PNG was exported. Select a synced metadata group.\n\n"
                + "\n".join(report.warnings[:8]),
            )
            return

        message = (
            f"Exported {report.exported_count} file(s).\n"
            f"Skipped {report.skipped_count} file(s).\n"
            f"Output: {output_dir}"
        )
        if report.warnings:
            message += "\n\nWarnings:\n" + "\n".join(report.warnings[:8])
        QMessageBox.information(None, "Krita AI Metadata Export", message)

    def _repair_empty_selected_records(self, document: Any, store: SyncMapStore) -> None:
        resolver = JobHistoryResolver()
        changed = False

        for layer in document.layers.all:
            record = store.resolve_group(group_id=layer.id_string, group_name=layer.name)
            if record is None:
                continue
            layers = layer.child_layers or [layer]
            snapshot = resolver.params_snapshot_for_layers(layers)
            if not snapshot:
                continue

            if record.params_snapshot == snapshot:
                continue

            record.params_snapshot = snapshot
            record.seed = int(snapshot.get("seed", 0) or 0)
            changed = True

        if changed:
            store.save()
            store.load()

    def _default_output_dir(self, document: Any) -> str:
        if document.filename:
            return str(Path(document.filename).parent / "krita_ai_metadata_export")
        return str(Path.home() / "krita_ai_metadata_export")
