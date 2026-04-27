from __future__ import annotations

from dataclasses import dataclass, field

from krita_ai_metadata.export_target_scanner import ExportMode, ExportTargetScanner


@dataclass
class FakeBounds:
    is_zero: bool = False


@dataclass
class FakeType:
    is_image: bool = True
    value: str = "paintlayer"

    def __eq__(self, other):
        return False


@dataclass
class FakeLayer:
    id_string: str
    name: str
    is_visible: bool = True
    bounds: FakeBounds = field(default_factory=FakeBounds)
    type: FakeType = field(default_factory=FakeType)
    parent_layer: object | None = None
    child_layers: list = field(default_factory=list)


@dataclass
class FakeLayerManager:
    all: list[FakeLayer]
    active: FakeLayer


@dataclass
class FakeSyncMapStore:
    records_by_layer_id: dict
    records_by_group_id: dict = field(default_factory=dict)
    records_by_group_name: dict = field(default_factory=dict)

    def resolve_layer(self, layer_id: str):
        return self.records_by_layer_id.get(layer_id)

    def resolve_group(self, group_id: str | None = None, group_name: str | None = None):
        if group_id and group_id in self.records_by_group_id:
            return self.records_by_group_id[group_id]
        if group_name and group_name in self.records_by_group_name:
            return self.records_by_group_name[group_name]
        return None


def test_scanner_resolves_layer_record_by_layer_id():
    layer = FakeLayer(id_string="{layer-1}", name="Layer 1")
    manager = FakeLayerManager(all=[layer], active=layer)
    store = FakeSyncMapStore(
        records_by_layer_id={
            "{layer-1}": {
                "target_type": "layer",
                "export_key": "0001-layer",
                "layer_ids": ["{layer-1}"],
                "params_snapshot": {},
            }
        }
    )

    targets = ExportTargetScanner().scan(manager, store, ExportMode.all)

    assert len(targets) == 1
    assert targets[0].is_resolved
    assert targets[0].key == "0001-layer"
    assert targets[0].target_type == "layer"


def test_scanner_marks_unresolved_target_warning():
    layer = FakeLayer(id_string="{layer-2}", name="Unmapped Layer")
    manager = FakeLayerManager(all=[layer], active=layer)
    store = FakeSyncMapStore(records_by_layer_id={})

    targets = ExportTargetScanner().scan(manager, store, ExportMode.all)

    assert len(targets) == 1
    assert not targets[0].is_resolved
    assert targets[0].warnings
    assert "No sync metadata" in targets[0].warnings[0]


def test_scanner_resolves_group_record_by_group_id():
    layer = FakeLayer(id_string="{group-1}", name="Group 1")
    manager = FakeLayerManager(all=[layer], active=layer)
    store = FakeSyncMapStore(
        records_by_layer_id={},
        records_by_group_id={
            "{group-1}": {
                "target_type": "group",
                "export_key": "0001-group",
                "group_id": "{group-1}",
                "group_name": "Group 1",
                "layer_ids": ["{child-1}"],
                "params_snapshot": {},
            }
        },
    )

    targets = ExportTargetScanner().scan(manager, store, ExportMode.all)

    assert len(targets) == 1
    assert targets[0].is_resolved
    assert targets[0].key == "0001-group"
    assert targets[0].target_type == "group"


def test_scanner_marks_parent_group_metadata_as_inherited():
    parent = FakeLayer(id_string="{group-2}", name="Parent Group")
    child = FakeLayer(id_string="{child-2}", name="Child Layer", parent_layer=parent)
    manager = FakeLayerManager(all=[child], active=child)
    store = FakeSyncMapStore(
        records_by_layer_id={},
        records_by_group_id={
            "{group-2}": {
                "target_type": "group",
                "export_key": "0002-group",
                "group_id": "{group-2}",
                "group_name": "Parent Group",
                "layer_ids": ["{child-2}"],
                "params_snapshot": {},
            }
        },
    )

    targets = ExportTargetScanner().scan(manager, store, ExportMode.all)

    assert len(targets) == 1
    assert targets[0].is_resolved
    assert targets[0].key == "0002-group"
    assert any("inherited from parent group" in warning for warning in targets[0].warnings)
