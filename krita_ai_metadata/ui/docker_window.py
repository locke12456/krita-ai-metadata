from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ai_diffusion_compat import active_model
from ..auto_mapping import AutoMappingService
from ..capabilities import build_feature_flags, refresh_feature_flags
from ..krita_core_adapter import active_krita_document, all_krita_nodes, selected_krita_nodes
from ..qt_compat import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from ..docker_export_runner import DockerExportRunner
from ..export_target_scanner import ExportMode
from ..layer_selection_model import LayerSelectionModel
from ..sync_map_store import SyncMapStore


class DockerWindow(QWidget):
    """Docker UI for explicit layer selection, auto mapping, preview, and export."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.selection_model = LayerSelectionModel()
        self.runner = DockerExportRunner()
        self.layer_manager: Any | None = None
        self.sync_map_store: Any | None = None
        self.document: Any | None = None
        self.feature_flags = build_feature_flags()
        self._layer_checks: dict[str, QCheckBox] = {}

        self._mode_label = QLabel(self.feature_flags.mode_label, self)
        self._status_label = QLabel("No active document.", self)
        self._selection_label = QLabel("Selected layers: 0", self)
        self._output_status_label = QLabel("", self)
        self._output_dir_user_set = False

        self._error_label = QLabel("", self)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: #d99a00; font-weight: bold;")
        self._error_label.setVisible(False)

        self._report_label = QLabel("", self)
        self._report_label.setWordWrap(True)

        self._refresh_button = QPushButton("Refresh", self)
        self._import_selection_button = QPushButton("Import current Krita selection", self)
        self._auto_map_button = QPushButton("Auto map selected layers", self)
        self._preview_button = QPushButton("Preview export", self)
        self._export_button = QPushButton("Export selected PNG metadata", self)

        self._filter_synced = QCheckBox("Synced / inherited", self)
        self._filter_unsynced = QCheckBox("Unsynced", self)
        self._filter_visible = QCheckBox("Visible", self)
        self._filter_hidden = QCheckBox("Hidden", self)
        self._filter_groups = QCheckBox("Groups", self)
        self._filter_layers = QCheckBox("Layers", self)

        for checkbox in (
            self._filter_synced,
            self._filter_unsynced,
            self._filter_visible,
            self._filter_hidden,
            self._filter_groups,
            self._filter_layers,
        ):
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._render_layer_rows)

        self._output_dir = QLineEdit(str(Path.home() / "krita_ai_metadata_export"), self)
        self._browse_button = QPushButton("Browse", self)
        self._overwrite_checkbox = QCheckBox("Overwrite existing PNG / JSON files", self)
        self._allow_unresolved_checkbox = QCheckBox("Allow unresolved AI metadata export", self)
        self._manifest_checkbox = QCheckBox("Write manifest JSON", self)
        self._manifest_checkbox.setChecked(True)
        self._include_invisible_checkbox = QCheckBox("Include invisible selected targets", self)
        self._group_label = QLineEdit("", self)
        self._group_label.setPlaceholderText("Group label for new metadata groups")

        self._mode_combo = QComboBox(self)
        self._mode_combo.addItem("Selected docker layers", ExportMode.selected)
        self._mode_combo.addItem("Visible targets", ExportMode.visible)
        self._mode_combo.addItem("All targets", ExportMode.all)

        self._layer_list_widget = QWidget(self)
        self._layer_list_layout = QVBoxLayout()
        self._layer_list_widget.setLayout(self._layer_list_layout)

        self._layer_scroll_area = QScrollArea(self)
        self._layer_scroll_area.setWidgetResizable(True)
        self._layer_scroll_area.setMinimumHeight(180)
        self._layer_scroll_area.setWidget(self._layer_list_widget)

        self._refresh_button.clicked.connect(self.refresh)
        self._import_selection_button.clicked.connect(self.import_current_selection)
        self._auto_map_button.clicked.connect(self.auto_map_selected)
        self._preview_button.clicked.connect(self.preview_export)
        self._export_button.clicked.connect(self.export_selected)
        self._browse_button.clicked.connect(self.choose_output_dir)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self._filter_synced)
        filter_layout.addWidget(self._filter_unsynced)
        filter_layout.addWidget(self._filter_visible)
        filter_layout.addWidget(self._filter_hidden)
        filter_layout.addWidget(self._filter_groups)
        filter_layout.addWidget(self._filter_layers)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output:", self))
        output_layout.addWidget(self._output_dir)
        output_layout.addWidget(self._browse_button)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Export mode:", self))
        mode_layout.addWidget(self._mode_combo)

        group_label_layout = QHBoxLayout()
        group_label_layout.addWidget(QLabel("Group label:", self))
        group_label_layout.addWidget(self._group_label)

        layout = QVBoxLayout()
        layout.addWidget(self._mode_label)
        layout.addWidget(self._status_label)
        layout.addWidget(self._error_label)
        layout.addWidget(self._selection_label)
        layout.addWidget(self._refresh_button)
        layout.addLayout(filter_layout)
        layout.addWidget(self._layer_scroll_area)
        layout.addWidget(self._import_selection_button)
        layout.addLayout(group_label_layout)
        layout.addWidget(self._auto_map_button)
        layout.addLayout(output_layout)
        layout.addWidget(self._output_status_label)
        layout.addLayout(mode_layout)
        layout.addWidget(self._overwrite_checkbox)
        layout.addWidget(self._allow_unresolved_checkbox)
        layout.addWidget(self._manifest_checkbox)
        layout.addWidget(self._include_invisible_checkbox)
        layout.addWidget(QLabel("PNG output only. JPEG / DPI / resize are future disabled options.", self))
        layout.addWidget(self._preview_button)
        layout.addWidget(self._export_button)
        layout.addWidget(self._report_label)
        layout.addStretch()
        self.setLayout(layout)

        self.refresh()

    def set_context(self, layer_manager: Any, sync_map_store: Any) -> None:
        """Set verified pipeline context from caller-owned integration code."""
        self.layer_manager = layer_manager
        self.sync_map_store = sync_map_store
        self.selection_model.rebuild(layer_manager, sync_map_store)
        self._sync_output_dir_with_document()
        self._render_layer_rows()
        self._update_labels()

    def refresh_from_canvas(self, canvas: Any) -> None:
        """Refresh state after Krita reports a canvas change."""
        self.refresh()

    def refresh(self) -> None:
        """Refresh active document, layer rows, and sync-map state."""
        self._clear_error()

        self.feature_flags = refresh_feature_flags()
        self.runner.feature_flags = self.feature_flags
        if hasattr(self.runner.resolver, "feature_flags"):
            self.runner.resolver.feature_flags = self.feature_flags
        self._mode_label.setText(self.feature_flags.mode_label)
        self._auto_map_button.setEnabled(
            self.feature_flags.prompt_search_enabled or self.feature_flags.manual_group_enabled
        )
        self._group_label.setEnabled(self.feature_flags.manual_group_enabled)
        self._preview_button.setEnabled(self.feature_flags.basic_export_enabled)
        self._export_button.setEnabled(self.feature_flags.basic_export_enabled)
        self._apply_mode_specific_option_labels()

        if not self.feature_flags.prompt_search_enabled:
            if self._refresh_manual_only_context():
                return
            self.document = None
            self.layer_manager = None
            self.sync_map_store = None
            self.selection_model.rows = []
            self._status_label.setText("No active document.")
            self._render_layer_rows()
            self._update_labels()
            return

        try:
            model = active_model()
        except Exception as exc:
            if self._refresh_manual_only_context():
                return
            self._show_error(f"Unable to read active document: {exc}")
            return

        if model is None:
            if self._refresh_manual_only_context():
                return
            self.document = None
            self.layer_manager = None
            self.sync_map_store = None
            self.selection_model.rows = []
            self._status_label.setText("No active document.")
            self._render_layer_rows()
            self._update_labels()
            return

        document = getattr(model, "document", None)
        layer_manager = getattr(document, "layers", None)

        if document is None or layer_manager is None:
            self._show_error("Active document loaded, but layer manager is unavailable.")
            return

        try:
            self.document = document
            self.layer_manager = layer_manager
            self.sync_map_store = SyncMapStore(document)
            self.selection_model.rebuild(layer_manager, self.sync_map_store)
            self._sync_output_dir_with_document()
            self._status_label.setText("Active document loaded.")
            if self.feature_flags.mode_warning:
                self._append_report(self.feature_flags.mode_warning)
            self._render_layer_rows()
            self._update_labels()
        except Exception as exc:
            self._show_error(f"Failed to refresh docker state: {exc}")

    def _refresh_manual_only_context(self) -> bool:
        """Refresh docker rows from native Krita adapters when AI Diffusion is unavailable."""
        document_ref = active_krita_document()
        if document_ref is None:
            return False

        all_nodes = all_krita_nodes(document_ref)
        selected_nodes = selected_krita_nodes()
        active = selected_nodes[0] if selected_nodes else (all_nodes[0] if all_nodes else None)
        layer_manager = type(
            "ManualLayerManager",
            (),
            {
                "all": all_nodes,
                "active": active,
                "update": lambda self: document_ref.refresh_projection(),
            },
        )()

        self.document = document_ref
        self.layer_manager = layer_manager
        self.sync_map_store = SyncMapStore(document_ref)
        self.selection_model.rebuild(layer_manager, self.sync_map_store)
        self.selection_model.select_layer_ids([node.id_string for node in selected_nodes])
        self._sync_output_dir_with_document()
        self._status_label.setText("Manual-only active document loaded.")
        if self.feature_flags.mode_warning:
            self._append_report(self.feature_flags.mode_warning)
        self._render_layer_rows()
        self._update_labels()
        return True

    def _apply_mode_specific_option_labels(self) -> None:
        """Make export option labels match AI-enabled vs manual-only behavior."""
        if not self.feature_flags.prompt_search_enabled:
            self._allow_unresolved_checkbox.setChecked(True)
            self._allow_unresolved_checkbox.setEnabled(False)
            self._allow_unresolved_checkbox.setText("Manual export without AI metadata")
            self._allow_unresolved_checkbox.setToolTip(
                "Manual-only mode has no Krita AI Diffusion metadata to resolve; "
                "exports are always written without AI prompt metadata."
            )
            self._manifest_checkbox.setText("Write manifest JSON")
            self._manifest_checkbox.setToolTip("Optional: write manifest.json for exported PNG/JSON files.")
            self._overwrite_checkbox.setText("Overwrite existing PNG / JSON files")
            self._include_invisible_checkbox.setText("Include invisible selected targets")
            return

        self._allow_unresolved_checkbox.setEnabled(True)
        self._allow_unresolved_checkbox.setText("Allow unresolved AI metadata export")
        self._allow_unresolved_checkbox.setToolTip(
            "When enabled, export targets that have no resolved AI metadata are still written."
        )
        self._manifest_checkbox.setText("Write manifest JSON")
        self._manifest_checkbox.setToolTip("Optional: write manifest.json for exported PNG/JSON files.")
        self._overwrite_checkbox.setText("Overwrite existing PNG / JSON files")
        self._include_invisible_checkbox.setText("Include invisible selected targets")

    def choose_output_dir(self) -> None:
        """Let the user choose the docker export output directory."""
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select AI metadata export folder",
            self._output_dir.text(),
        )
        if selected:
            self._output_dir_user_set = True
            self._output_dir.setText(selected)
            self._output_status_label.setText("Output folder manually selected.")

    def import_current_selection(self) -> None:
        """Explicitly import current Krita selection into docker-owned selection."""
        if self.layer_manager is None:
            self._show_error("Layer manager is not available.")
            return

        self.selection_model.import_krita_selection(self.layer_manager)
        self._render_layer_rows()
        self._update_labels()

    def auto_map_selected(self) -> None:
        """Run headless auto mapping for selected rows, then refresh preview state."""
        if self.layer_manager is None or self.sync_map_store is None:
            self._show_error("Auto mapping requires layer manager and sync map context.")
            return

        if not self.feature_flags.prompt_search_enabled and not self.feature_flags.manual_group_enabled:
            self._show_error(self.feature_flags.mode_warning or "Prompt search is disabled.")
            return

        layers = self._selected_layers()
        if not layers:
            self._show_error("No docker-selected layers to auto map.")
            return

        manual_label = self._group_label.text().strip()
        if not manual_label:
            self._show_error("Please enter a group label before auto mapping.")
            return

        try:
            service = AutoMappingService(self.layer_manager, self.sync_map_store)
            if self.feature_flags.prompt_search_enabled:
                result = service.auto_map_with_ai_history(layers, manual_label=manual_label)
            else:
                result = service.create_manual_group_record(layers, manual_label=manual_label)
            self.sync_map_store.load()
            self.selection_model.rebuild(self.layer_manager, self.sync_map_store)
            self._render_layer_rows()
            self._update_labels()
            self.preview_export()
            self._append_report(
                f"Auto mapped records: {result.mapped_count}; warnings: {len(result.warnings)}"
            )
        except Exception as exc:
            self._show_error(f"Auto mapping failed: {exc}")

    def preview_export(self) -> None:
        """Run read-only preview for the explicit docker selection."""
        if self.layer_manager is None or self.sync_map_store is None:
            self._show_error("Preview requires layer manager and sync map context.")
            return

        options = self._current_options()
        report = self.runner.preview(self.layer_manager, self.sync_map_store, options)
        display_report_warnings = self._display_warnings(report.warnings)
        lines = [f"Preview targets: {len(report.rows)}; warnings: {len(display_report_warnings)}"]

        for row in report.rows[:12]:
            state = "resolved" if row.resolved else "unresolved"
            if row.inherited:
                state += " / inherited"
            lines.append(f"- {row.key}: {row.layer_name} ({state}) -> {row.output_path}")

        for warning in display_report_warnings[:8]:
            lines.append(f"Warning: {warning}")

        self._report_label.setText("\n".join(lines))

    def export_selected(self) -> None:
        """Run docker export for explicit selected layers through the PNG pipeline."""
        if self.layer_manager is None or self.sync_map_store is None:
            self._show_error("Export requires layer manager and sync map context.")
            return

        options = self._current_options()
        try:
            report = self.runner.export(self.layer_manager, self.sync_map_store, options)
        except Exception as exc:
            self._show_error(f"Export failed: {exc}")
            return

        display_warnings = self._display_warnings(report.warnings)
        lines = [
            f"Exported: {report.exported_count}; skipped: {report.skipped_count}; warnings: {len(display_warnings)}"
        ]
        if report.aborted:
            lines.append("Export aborted.")

        for result in report.results[:12]:
            lines.append(f"- {result.key}: {result.png_path or 'not written'}")

        for warning in display_warnings[:8]:
            lines.append(f"Warning: {warning}")

        self._report_label.setText("\n".join(lines))

    def _render_layer_rows(self) -> None:
        self._clear_layer_checks()
        if self.layer_manager is None or self.sync_map_store is None:
            return

        selected = set(self.selection_model.selected_layer_ids)
        rows = self.selection_model.filtered_rows(
            show_synced=self._filter_synced.isChecked(),
            show_unsynced=self._filter_unsynced.isChecked(),
            show_visible=self._filter_visible.isChecked(),
            show_hidden=self._filter_hidden.isChecked(),
            show_groups=self._filter_groups.isChecked(),
            show_layers=self._filter_layers.isChecked(),
        )

        for row in rows:
            label = self._row_label(row)
            checkbox = QCheckBox(label, self)
            checkbox.setChecked(row.layer_id in selected)
            checkbox.stateChanged.connect(self._on_layer_checked)
            self._layer_checks[row.layer_id] = checkbox
            self._layer_list_layout.addWidget(checkbox)

        self._layer_list_layout.addStretch()

    def _clear_layer_checks(self) -> None:
        while self._layer_list_layout.count():
            item = self._layer_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._layer_checks = {}

    def _on_layer_checked(self) -> None:
        selected_ids = [
            layer_id
            for layer_id, checkbox in self._layer_checks.items()
            if checkbox.isChecked()
        ]
        self.selection_model.select_layer_ids(selected_ids)
        self._update_labels()

    def _selected_layers(self) -> list[Any]:
        if self.layer_manager is None:
            return []

        selected = set(self.selection_model.selected_layer_ids)
        return [
            layer
            for layer in self.layer_manager.all
            if layer.id_string in selected
        ]

    def _sync_output_dir_with_document(self) -> None:
        if self._output_dir_user_set:
            return

        filename = str(getattr(self.document, "filename", "") or "")
        if filename:
            folder = Path(filename).parent / "krita_ai_metadata_export"
            self._output_dir.setText(str(folder))
            self._output_status_label.setText("Output folder synced to saved .kra location.")
            return

        fallback = Path.home() / "krita_ai_metadata_export"
        self._output_dir.setText(str(fallback))
        self._output_status_label.setText("Document is unsaved. Using home export folder.")

    def _current_options(self):
        return self.selection_model.to_export_options(
            output_dir=self._output_dir.text() or ".",
            mode=self._current_export_mode(),
            overwrite=self._overwrite_checkbox.isChecked(),
            allow_unresolved=self._allow_unresolved_checkbox.isChecked(),
            write_manifest=self._manifest_checkbox.isChecked(),
            include_invisible_targets=self._include_invisible_checkbox.isChecked(),
        )

    def _current_export_mode(self) -> ExportMode:
        mode = self._mode_combo.currentData()
        if isinstance(mode, ExportMode):
            return mode
        return ExportMode(str(mode))

    def _row_label(self, row) -> str:
        kind = "Group" if row.is_group else "Layer"
        visibility = "visible" if row.visible else "hidden"
        return f"{row.name} — {kind}, {visibility}, {row.metadata_state}"

    def _update_labels(self) -> None:
        self._selection_label.setText(
            f"Selected layers: {len(self.selection_model.selected_layer_ids)}"
        )

    def _display_warnings(self, warnings: list[str]) -> list[str]:
        """Hide AI-metadata implementation details in manual export mode."""
        if self.feature_flags.prompt_search_enabled:
            return list(warnings)

        hidden_fragments = (
            "Krita AI Diffusion",
            "prompt search disabled",
            "No metadata available for",
        )
        return [
            warning
            for warning in warnings
            if not any(fragment in warning for fragment in hidden_fragments)
        ]

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setVisible(True)
        self._report_label.setText(message)

    def _clear_error(self) -> None:
        self._error_label.setText("")
        self._error_label.setVisible(False)

    def _append_report(self, message: str) -> None:
        current = self._report_label.text()
        self._report_label.setText((current + "\n" + message).strip())
