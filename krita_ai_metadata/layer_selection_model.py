from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ai_diffusion_compat import is_group_layer

from .export_options import ExportOptions
from .export_target_scanner import ExportMode
from .krita_view_adapter import KritaViewAdapter


@dataclass(slots=True)
class LayerSelectionRow:
    """UI-friendly row for one Krita layer or group."""

    layer_id: str
    name: str
    layer_type: str
    visible: bool
    is_group: bool
    synced: bool
    inherited: bool
    metadata_state: str
    parent_group_id: str | None = None
    parent_group_name: str | None = None


@dataclass
class LayerSelectionModel:
    """Docker-owned layer multi-selection state."""

    rows: list[LayerSelectionRow] = field(default_factory=list)
    selected_layer_ids: list[str] = field(default_factory=list)
    selected_group_ids: list[str] = field(default_factory=list)

    def rebuild(self, layer_manager: Any, sync_map_store: Any) -> None:
        """Rebuild row state from Krita layers and sync-map records."""
        rows: list[LayerSelectionRow] = []

        for layer in layer_manager.all:
            if layer.is_root:
                continue

            row = self._row_for_layer(layer, sync_map_store)
            rows.append(row)

        self.rows = rows
        valid_ids = {row.layer_id for row in rows}
        self.selected_layer_ids = [layer_id for layer_id in self.selected_layer_ids if layer_id in valid_ids]
        self.selected_group_ids = [layer_id for layer_id in self.selected_group_ids if layer_id in valid_ids]

    def select_layer_ids(self, layer_ids: list[str]) -> None:
        """Replace docker selection with explicit layer IDs."""
        result: list[str] = []
        seen: set[str] = set()

        for layer_id in layer_ids:
            if not layer_id or layer_id in seen:
                continue
            seen.add(layer_id)
            result.append(layer_id)

        self.selected_layer_ids = result
        group_ids = {row.layer_id for row in self.rows if row.is_group}
        self.selected_group_ids = [layer_id for layer_id in result if layer_id in group_ids]

    def import_krita_selection(
        self,
        layer_manager: Any,
        view_adapter: KritaViewAdapter | None = None,
    ) -> None:
        """Explicitly copy current Krita native selection into docker selection."""
        adapter = view_adapter or KritaViewAdapter()
        layers = adapter.unique_selected_layers(layer_manager)
        self.select_layer_ids([layer.id_string for layer in layers])

    def selected_rows(self) -> list[LayerSelectionRow]:
        """Return row records for the current explicit docker selection."""
        selected = set(self.selected_layer_ids)
        return [row for row in self.rows if row.layer_id in selected]

    def filtered_rows(
        self,
        show_synced: bool = True,
        show_unsynced: bool = True,
        show_visible: bool = True,
        show_hidden: bool = True,
        show_groups: bool = True,
        show_layers: bool = True,
    ) -> list[LayerSelectionRow]:
        """Return rows after applying docker UI filters."""
        result: list[LayerSelectionRow] = []

        for row in self.rows:
            if row.synced or row.inherited:
                if not show_synced:
                    continue
            elif not show_unsynced:
                continue

            if row.visible:
                if not show_visible:
                    continue
            elif not show_hidden:
                continue

            if row.is_group:
                if not show_groups:
                    continue
            elif not show_layers:
                continue

            result.append(row)

        return result

    def to_export_options(
        self,
        output_dir: str | Path,
        mode: ExportMode = ExportMode.selected,
        overwrite: bool = False,
        allow_unresolved: bool = False,
        write_manifest: bool = True,
        include_invisible_targets: bool = False,
    ) -> ExportOptions:
        """Build normalized docker export options from current selection."""
        return ExportOptions(
            output_dir=output_dir,
            mode=mode,
            selected_layer_ids=list(self.selected_layer_ids),
            overwrite=overwrite,
            allow_unresolved=allow_unresolved,
            write_manifest=write_manifest,
            include_invisible_targets=include_invisible_targets,
            image_extension="png",
        )

    def _row_for_layer(self, layer: Any, sync_map_store: Any) -> LayerSelectionRow:
        layer_record = sync_map_store.resolve_layer(layer.id_string)
        group_record = sync_map_store.resolve_group(group_id=layer.id_string, group_name=layer.name)

        parent = layer.parent_layer
        parent_record = None
        if parent is not None:
            parent_record = sync_map_store.resolve_group(
                group_id=parent.id_string,
                group_name=parent.name,
            )

        synced = layer_record is not None or group_record is not None
        inherited = not synced and parent_record is not None

        if synced:
            metadata_state = "synced"
        elif inherited:
            metadata_state = "inherited"
        else:
            metadata_state = "unsynced"

        return LayerSelectionRow(
            layer_id=layer.id_string,
            name=layer.name,
            layer_type=str(getattr(getattr(layer, "type", ""), "value", getattr(layer, "type", ""))),
            visible=layer.is_visible,
            is_group=is_group_layer(layer),
            synced=synced,
            inherited=inherited,
            metadata_state=metadata_state,
            parent_group_id=parent.id_string if parent is not None else None,
            parent_group_name=parent.name if parent is not None else None,
        )