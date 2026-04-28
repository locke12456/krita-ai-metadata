from pathlib import Path
from types import SimpleNamespace

from krita_ai_metadata import ai_diffusion_compat
from fakes.fake_ai_diffusion import FakeLayerType

from krita_ai_metadata.export_target_scanner import ExportMode
from krita_ai_metadata.layer_selection_model import LayerSelectionModel


class FakeLayer:
    def __init__(
        self,
        layer_id: str,
        name: str,
        layer_type: FakeLayerType,
        visible: bool = True,
        parent_layer=None,
        is_root: bool = False,
    ):
        self.id_string = layer_id
        self.name = name
        self.type = layer_type
        self.is_visible = visible
        self.parent_layer = parent_layer
        self.is_root = is_root


class FakeStore:
    def __init__(self, layer_records=None, group_records=None):
        self.layer_records = layer_records or {}
        self.group_records = group_records or {}

    def resolve_layer(self, layer_id: str):
        return self.layer_records.get(layer_id)

    def resolve_group(self, group_id=None, group_name=None):
        if group_id in self.group_records:
            return self.group_records[group_id]
        return self.group_records.get(group_name)


class FakeViewAdapter:
    def __init__(self, layers):
        self.layers = layers

    def unique_selected_layers(self, layer_manager):
        return list(self.layers)


def test_rebuild_marks_synced_inherited_and_unsynced_rows(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "LayerType", FakeLayerType)
    root = FakeLayer("root", "Root", FakeLayerType.group, is_root=True)
    synced_group = FakeLayer("group-1", "Synced Group", FakeLayerType.group, parent_layer=root)
    inherited_child = FakeLayer("child-1", "Inherited Child", FakeLayerType.paint, parent_layer=synced_group)
    unsynced = FakeLayer("layer-2", "Unsynced", FakeLayerType.paint, parent_layer=root)
    manager = SimpleNamespace(all=[root, synced_group, inherited_child, unsynced])
    store = FakeStore(group_records={"group-1": {"export_key": "group"}})

    model = LayerSelectionModel()
    model.rebuild(manager, store)

    states = {row.layer_id: row.metadata_state for row in model.rows}

    assert "root" not in states
    assert states["group-1"] == "synced"
    assert states["child-1"] == "inherited"
    assert states["layer-2"] == "unsynced"


def test_select_layer_ids_deduplicates_and_tracks_selected_groups(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "LayerType", FakeLayerType)
    group = FakeLayer("group-1", "Group", FakeLayerType.group)
    layer = FakeLayer("layer-1", "Layer", FakeLayerType.paint)
    manager = SimpleNamespace(all=[group, layer])
    model = LayerSelectionModel()
    model.rebuild(manager, FakeStore())

    model.select_layer_ids(["", "group-1", "layer-1", "group-1"])

    assert model.selected_layer_ids == ["group-1", "layer-1"]
    assert model.selected_group_ids == ["group-1"]
    assert [row.layer_id for row in model.selected_rows()] == ["group-1", "layer-1"]


def test_import_krita_selection_copies_explicit_ids() -> None:
    layer = FakeLayer("layer-1", "Layer", FakeLayerType.paint)
    model = LayerSelectionModel()

    model.import_krita_selection(
        SimpleNamespace(all=[layer]),
        view_adapter=FakeViewAdapter([layer]),
    )

    assert model.selected_layer_ids == ["layer-1"]


def test_filtered_rows_supports_sync_visibility_and_type_filters(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "LayerType", FakeLayerType)
    synced_group = FakeLayer("group-1", "Group", FakeLayerType.group, visible=True)
    hidden_layer = FakeLayer("layer-1", "Hidden", FakeLayerType.paint, visible=False)
    manager = SimpleNamespace(all=[synced_group, hidden_layer])
    store = FakeStore(group_records={"group-1": {"export_key": "group"}})
    model = LayerSelectionModel()
    model.rebuild(manager, store)

    assert [row.layer_id for row in model.filtered_rows(show_layers=False)] == ["group-1"]
    assert [row.layer_id for row in model.filtered_rows(show_groups=False)] == ["layer-1"]
    assert [row.layer_id for row in model.filtered_rows(show_hidden=False)] == ["group-1"]
    assert [row.layer_id for row in model.filtered_rows(show_synced=False)] == ["layer-1"]


def test_to_export_options_carries_selection_and_flags(tmp_path: Path) -> None:
    model = LayerSelectionModel()
    model.select_layer_ids(["layer-1"])

    options = model.to_export_options(
        output_dir=tmp_path,
        mode=ExportMode.all,
        overwrite=True,
        allow_unresolved=True,
        write_manifest=False,
        include_invisible_targets=True,
    )

    assert options.output_dir == tmp_path
    assert options.mode == ExportMode.all
    assert options.selected_layer_ids == ["layer-1"]
    assert options.overwrite is True
    assert options.allow_unresolved is True
    assert options.write_manifest is False
    assert options.include_invisible_targets is True
    assert options.image_extension == "png"