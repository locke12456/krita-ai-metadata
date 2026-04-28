from types import SimpleNamespace

from krita_ai_metadata import ai_diffusion_compat
from tests.fakes.fake_ai_diffusion import FakeLayerType

from krita_ai_metadata.export_target_scanner import ExportMode, ExportTargetScanner


class FakeBounds:
    def __init__(self, is_zero: bool = False):
        self.is_zero = is_zero


class FakeLayer:
    def __init__(
        self,
        layer_id: str,
        name: str,
        layer_type: FakeLayerType = FakeLayerType.paint,
        visible: bool = True,
        is_zero: bool = False,
        parent_layer=None,
    ):
        self.id_string = layer_id
        self.name = name
        self.type = layer_type
        self.is_visible = visible
        self.bounds = FakeBounds(is_zero)
        self.parent_layer = parent_layer


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
    def __init__(self, selected=None):
        self.selected = selected or []

    def unique_selected_layers(self, layer_manager):
        return list(self.selected)


def test_scan_selected_ids_resolves_group_and_layer_records(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "LayerType", FakeLayerType)
    group = FakeLayer("group-1", "Group", FakeLayerType.group)
    layer = FakeLayer("layer-1", "Layer", FakeLayerType.paint)
    manager = SimpleNamespace(all=[group, layer])
    store = FakeStore(
        layer_records={"layer-1": {"export_key": "layer-key", "target_type": "layer"}},
        group_records={"group-1": {"export_key": "group-key", "target_type": "group"}},
    )

    targets = ExportTargetScanner().scan_selected_ids(
        manager,
        store,
        ["group-1", "layer-1"],
    )

    assert [target.key for target in targets] == ["group-key", "layer-key"]
    assert [target.target_type for target in targets] == ["group", "layer"]
    assert all(target.is_resolved for target in targets)


def test_scan_selected_ids_skips_hidden_without_include_flag_and_warns() -> None:
    hidden = FakeLayer("layer-1", "Hidden Layer", visible=False)
    scanner = ExportTargetScanner()

    targets = scanner.scan_selected_ids(
        SimpleNamespace(all=[hidden]),
        FakeStore(),
        ["layer-1"],
        include_invisible_targets=False,
    )

    assert targets == []
    assert scanner.last_warnings == ["Hidden selected target 'Hidden Layer' was skipped."]


def test_scan_selected_ids_includes_hidden_with_include_flag() -> None:
    hidden = FakeLayer("layer-1", "Hidden Layer", visible=False)

    targets = ExportTargetScanner().scan_selected_ids(
        SimpleNamespace(all=[hidden]),
        FakeStore(layer_records={"layer-1": {"export_key": "hidden-key"}}),
        ["layer-1"],
        include_invisible_targets=True,
    )

    assert [target.key for target in targets] == ["hidden-key"]


def test_visible_mode_ignores_include_invisible_targets() -> None:
    visible = FakeLayer("visible", "Visible", visible=True)
    hidden = FakeLayer("hidden", "Hidden", visible=False)
    scanner = ExportTargetScanner(view_adapter=FakeViewAdapter())

    targets = scanner.scan(
        SimpleNamespace(all=[visible, hidden]),
        FakeStore(),
        ExportMode.visible,
        include_invisible_targets=True,
    )

    assert [target.layer.id_string for target in targets] == ["visible"]


def test_all_mode_respects_include_invisible_targets() -> None:
    visible = FakeLayer("visible", "Visible", visible=True)
    hidden = FakeLayer("hidden", "Hidden", visible=False)
    scanner = ExportTargetScanner(view_adapter=FakeViewAdapter())
    manager = SimpleNamespace(all=[visible, hidden])

    visible_only = scanner.scan(manager, FakeStore(), ExportMode.all, include_invisible_targets=False)
    all_targets = scanner.scan(manager, FakeStore(), ExportMode.all, include_invisible_targets=True)

    assert [target.layer.id_string for target in visible_only] == ["visible"]
    assert [target.layer.id_string for target in all_targets] == ["visible", "hidden"]


def test_child_layer_inherits_parent_group_metadata(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "LayerType", FakeLayerType)
    parent = FakeLayer("group-1", "Parent Group", FakeLayerType.group)
    child = FakeLayer("layer-1", "Child Layer", FakeLayerType.paint, parent_layer=parent)
    store = FakeStore(group_records={"group-1": {"export_key": "parent-key", "target_type": "group"}})

    targets = ExportTargetScanner().scan_selected_ids(
        SimpleNamespace(all=[child]),
        store,
        ["layer-1"],
    )

    assert len(targets) == 1
    assert targets[0].key == "parent-key"
    assert targets[0].warnings == [
        "Metadata for layer 'Child Layer' inherited from parent group 'Parent Group'."
    ]