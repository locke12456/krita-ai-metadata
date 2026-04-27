from __future__ import annotations

from dataclasses import dataclass, field

from krita_export_plugin.export_target_scanner import ExportMode, ExportTargetScanner


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