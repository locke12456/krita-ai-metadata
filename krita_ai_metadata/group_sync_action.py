from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ai_diffusion_compat import active_document, is_group_layer, refresh_projection
from .group_key import GroupKeyResolver
from .qt_compat import QInputDialog, QMessageBox
from .job_history_resolver import JobHistoryResolver
from .krita_core_adapter import active_krita_document, create_group_for_nodes, selected_krita_nodes
from .krita_view_adapter import KritaViewAdapter
from .layer_move_adapter import LayerMoveAdapter
from .sync_map_store import SyncMapStore, SyncRecord


@dataclass(slots=True)
class AddGroupResult:
    group_name: str
    export_key: str
    moved_count: int


class MetadataGroupAction:
    def __init__(self, view_adapter: KritaViewAdapter | None = None):
        self.view_adapter = view_adapter or KritaViewAdapter()
        self.key_resolver = GroupKeyResolver()
        self.job_resolver = JobHistoryResolver()

    def run_from_krita(self) -> AddGroupResult | None:
        try:
            document = active_document()
        except Exception:
            document = None

        if document is None:
            return self._run_manual_only()

        ok, message = document.check_color_mode()
        if not ok:
            QMessageBox.warning(None, "Krita AI Metadata", message or "Document is not compatible.")
            return None

        layers = self._selected_or_active_layers(document)
        layers = self._filter_top_level_selection(layers)
        layers = [layer for layer in layers if not layer.is_root]
        if not layers:
            QMessageBox.warning(None, "Krita AI Metadata", "No selected or active layer to group.")
            return None

        params_snapshot = self.job_resolver.params_snapshot_for_layers(layers)

        store = SyncMapStore(document)
        sync_index = store.allocate_sync_index()
        seed = int(params_snapshot.get("seed", 0) or 0)
        job_id = str(params_snapshot.get("job_id", "manual") or "manual")
        default_key = self.key_resolver.resolve(sync_index, job_id, 0, seed)

        group_name, accepted = QInputDialog.getText(
            None,
            "Add AI Metadata Group",
            "Group key/name:",
            text=default_key.group_name,
        )
        if not accepted:
            return None

        group_name = group_name.strip() or default_key.group_name
        export_key = self.key_resolver.sanitize(group_name)
        mover = LayerMoveAdapter(document.layers)

        first = layers[0]
        if is_group_layer(first):
            group = first
            group.name = group_name
        else:
            group = mover.create_group_for_layer(first, group_name)

        for layer in layers[1:]:
            if layer == group or layer.is_root:
                continue
            mover.move_to_group(layer, group)

        document.layers.update()
        group.refresh()
        refresh_projection(document)

        children = group.child_layers
        child_ids = [child.id_string for child in children]
        record = SyncRecord(
            target_type="group",
            export_key=export_key,
            layer_ids=child_ids,
            group_id=group.id_string,
            group_name=group.name,
            job_id=job_id,
            image_index=0,
            seed=seed,
            params_snapshot=params_snapshot,
            job_id_short=job_id[:8],
            sync_index=sync_index,
        )
        store.record_apply(record)

        meta_state = "with metadata" if params_snapshot else "without metadata"
        QMessageBox.information(
            None,
            "Krita AI Metadata",
            f"Created group: {group.name}\nChildren: {len(child_ids)}\nSync: {meta_state}",
        )
        return AddGroupResult(group.name, export_key, len(child_ids))

    def _run_manual_only(self) -> AddGroupResult | None:
        document_ref = active_krita_document()
        if document_ref is None:
            QMessageBox.warning(None, "Krita AI Metadata", "No active Krita document.")
            return None

        ok, message = document_ref.check_color_mode()
        if not ok:
            QMessageBox.warning(None, "Krita AI Metadata", message or "Document is not compatible.")
            return None

        nodes = [node for node in selected_krita_nodes() if not node.is_root]
        nodes = self._filter_top_level_selection(nodes)
        if not nodes:
            QMessageBox.warning(None, "Krita AI Metadata", "No selected layer to group.")
            return None

        store = SyncMapStore(document_ref)
        sync_index = store.allocate_sync_index()
        default_key = self.key_resolver.resolve(sync_index, "manual", 0, 0)

        group_name, accepted = QInputDialog.getText(
            None,
            "Add AI Metadata Group",
            "Group key/name:",
            text=default_key.group_name,
        )
        if not accepted:
            return None

        group_name = group_name.strip() or default_key.group_name
        export_key = self.key_resolver.sanitize(group_name)
        group = create_group_for_nodes(document_ref, nodes, group_name)
        document_ref.refresh_projection()

        child_ids = [child.id_string for child in group.child_layers]
        record = SyncRecord(
            target_type="group",
            export_key=export_key,
            layer_ids=child_ids,
            group_id=group.id_string,
            group_name=group.name,
            job_id="manual",
            image_index=0,
            seed=0,
            params_snapshot={},
            job_id_short="manual",
            sync_index=sync_index,
            manual_label=group_name,
        )
        store.record_apply(record)

        QMessageBox.information(
            None,
            "Krita AI Metadata",
            f"Created manual-only group: {group.name}\nChildren: {len(child_ids)}\nSync: without AI metadata",
        )
        return AddGroupResult(group.name, export_key, len(child_ids))

    def _selected_or_active_layers(self, document: Any) -> list[Any]:
        selected = self.view_adapter.unique_selected_layers(document.layers)
        if selected:
            return selected
        active = document.layers.active
        return [active] if active is not None else []

    def _filter_top_level_selection(self, layers: list[Any]) -> list[Any]:
        selected_ids = {layer.id_string for layer in layers}
        result: list[Any] = []
        for layer in layers:
            parent = layer.parent_layer
            skip = False
            while parent is not None:
                if parent.id_string in selected_ids:
                    skip = True
                    break
                parent = parent.parent_layer
            if not skip:
                result.append(layer)
        return result
