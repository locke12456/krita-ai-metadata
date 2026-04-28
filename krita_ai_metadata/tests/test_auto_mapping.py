from fakes.fake_ai_diffusion import FakeLayerType

from krita_ai_metadata.auto_mapping import AutoMappingService
from krita_ai_metadata.sync_map_store import SyncRecord


class FakeLayer:
    def __init__(
        self,
        layer_id: str,
        name: str,
        parent_layer=None,
        is_root: bool = False,
    ):
        self.id_string = layer_id
        self.name = name
        self.parent_layer = parent_layer
        self.is_root = is_root
        self.type = FakeLayerType.paint
        self.refreshed = False

    def refresh(self) -> None:
        self.refreshed = True


class FakeLayerManager:
    def __init__(self):
        self.updated = 0

    def update(self) -> None:
        self.updated += 1


class FakeStore:
    def __init__(self):
        self.layer_records = {}
        self.group_records = {}
        self.applied = []
        self.loaded = 0
        self.next_sync_index = 1

    def allocate_sync_index(self) -> int:
        value = self.next_sync_index
        self.next_sync_index += 1
        return value

    def resolve_layer(self, layer_id: str):
        return self.layer_records.get(layer_id)

    def resolve_group(self, group_id=None, group_name=None):
        if group_id in self.group_records:
            return self.group_records[group_id]
        return self.group_records.get(group_name)

    def record_apply(self, record):
        self.applied.append(record)
        if record.group_id:
            self.group_records[record.group_id] = record
        if record.group_name:
            self.group_records[record.group_name] = record
        return record

    def load(self) -> None:
        self.loaded += 1


class FakeMover:
    def __init__(self):
        self.groups = []

    def create_group_for_layer(self, layer, group_name: str):
        group = FakeLayer(f"group-{layer.id_string}", group_name)
        self.groups.append((layer, group))
        return group


class FakeJobHistoryResolver:
    def __init__(self, snapshot=None):
        self.snapshot = snapshot or {}
        self.calls = []

    def params_snapshot_for_layers(self, layers):
        self.calls.append(list(layers))
        return dict(self.snapshot)


def make_record(target_type: str = "layer", group_id=None, group_name=None) -> SyncRecord:
    return SyncRecord(
        target_type=target_type,
        export_key="export-key",
        layer_ids=["layer-1"],
        job_id="job-123456789",
        image_index=2,
        seed=99,
        params_snapshot={"prompt": "test"},
        group_id=group_id,
        group_name=group_name,
        job_id_short="job-1234",
        sync_index=7,
        manual_label="castle-test-A",
    )


def test_layer_record_is_converted_to_group_record() -> None:
    layer = FakeLayer("layer-1", "Layer")
    manager = FakeLayerManager()
    store = FakeStore()
    store.layer_records["layer-1"] = make_record()
    mover = FakeMover()
    service = AutoMappingService(manager, store, mover=mover)

    result = service.auto_map([layer], manual_label="castle-test-A")

    assert result.mapped_count == 1
    assert result.records[0].target_type == "group"
    assert result.records[0].group_id == "group-layer-1"
    assert result.records[0].group_name == "[0007] - castle-test-A - img2"
    assert result.records[0].export_key == "0007-castle-test-A-img2"
    assert result.records[0].manual_label == "castle-test-A"
    assert store.applied == result.records
    assert store.loaded >= 2
    assert manager.updated >= 2
    assert mover.groups[0][0] is layer


def test_unsynced_layer_uses_job_history_snapshot() -> None:
    layer = FakeLayer("layer-1", "Layer")
    store = FakeStore()
    resolver = FakeJobHistoryResolver(
        {
            "job_id": "job-abcdef",
            "image_index": 3,
            "seed": 123,
            "prompt": "snapshot",
        }
    )
    service = AutoMappingService(
        FakeLayerManager(),
        store,
        job_history_resolver=resolver,
        mover=FakeMover(),
    )

    result = service.auto_map([layer], manual_label="castle-test-A")

    assert result.mapped_count == 1
    assert result.records[0].export_key == "0001-castle-test-A-img3"
    assert result.records[0].group_name == "[0001] - castle-test-A - img3"
    assert result.records[0].manual_label == "castle-test-A"
    assert result.records[0].job_id == "job-abcdef"
    assert result.records[0].image_index == 3
    assert result.records[0].seed == 123
    assert resolver.calls == [[layer]]


def test_existing_parent_group_record_is_inherited_without_write() -> None:
    parent = FakeLayer("group-1", "Parent Group")
    layer = FakeLayer("layer-1", "Layer", parent_layer=parent)
    inherited_record = make_record(target_type="group", group_id="group-1", group_name="Parent Group")
    store = FakeStore()
    store.group_records["group-1"] = inherited_record
    service = AutoMappingService(FakeLayerManager(), store, mover=FakeMover())

    result = service.auto_map([layer], manual_label="castle-test-A")

    assert result.records == [inherited_record]
    assert result.warnings == ["Layer 'Layer' already inherits metadata from group 'Parent Group'."]
    assert store.applied == []


def test_ambiguous_layer_and_parent_records_warns_and_skips() -> None:
    parent = FakeLayer("group-1", "Parent Group")
    layer = FakeLayer("layer-1", "Layer", parent_layer=parent)
    store = FakeStore()
    store.layer_records["layer-1"] = make_record()
    store.group_records["group-1"] = make_record(
        target_type="group",
        group_id="group-1",
        group_name="Parent Group",
    )
    service = AutoMappingService(FakeLayerManager(), store, mover=FakeMover())

    result = service.auto_map([layer], manual_label="castle-test-A")

    assert result.records == []
    assert result.warnings == [
        "Ambiguous metadata for layer 'Layer': layer record and parent group record both exist."
    ]
    assert store.applied == []


def test_repair_uses_auto_map_path() -> None:
    layer = FakeLayer("layer-1", "Layer")
    store = FakeStore()
    store.layer_records["layer-1"] = make_record()
    service = AutoMappingService(FakeLayerManager(), store, mover=FakeMover())

    result = service.repair([layer], manual_label="castle-test-A")

    assert result.mapped_count == 1


def test_empty_manual_label_blocks_auto_mapping() -> None:
    layer = FakeLayer("layer-1", "Layer")
    store = FakeStore()
    resolver = FakeJobHistoryResolver({"seed": 123, "prompt": "snapshot"})
    service = AutoMappingService(
        FakeLayerManager(),
        store,
        job_history_resolver=resolver,
        mover=FakeMover(),
    )

    result = service.auto_map([layer], manual_label="")

    assert result.records == []
    assert result.warnings == ["Please enter a group label before auto mapping."]
    assert store.applied == []

def test_manual_group_record_does_not_use_job_history_snapshot() -> None:
    layer = FakeLayer("layer-1", "Layer")
    store = FakeStore()
    resolver = FakeJobHistoryResolver({"seed": 123, "prompt": "snapshot"})
    service = AutoMappingService(
        FakeLayerManager(),
        store,
        job_history_resolver=resolver,
        mover=FakeMover(),
    )

    result = service.create_manual_group_record([layer], manual_label="manual-label")

    assert result.mapped_count == 1
    assert result.records[0].job_id == "manual"
    assert result.records[0].params_snapshot == {}
    assert resolver.calls == []

