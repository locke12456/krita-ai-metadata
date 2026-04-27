from __future__ import annotations

import pytest

from krita_ai_metadata.sync_map_store import SCHEMA_VERSION, SyncMapStore, SyncRecord


def test_migrate_raw_adds_missing_schema_fields():
    store = object.__new__(SyncMapStore)

    migrated = store._migrate_raw({})

    assert migrated["version"] == SCHEMA_VERSION
    assert migrated["next_sync_index"] == 1
    assert migrated["records_by_layer_id"] == {}
    assert migrated["records_by_group_id"] == {}
    assert migrated["records_by_group_name"] == {}


def test_migrate_raw_rejects_future_schema_version():
    store = object.__new__(SyncMapStore)

    with pytest.raises(ValueError):
        store._migrate_raw({"version": SCHEMA_VERSION + 1})


def test_sync_record_loads_missing_manual_label_as_empty_string():
    record = SyncRecord.from_dict(
        {
            "target_type": "group",
            "export_key": "legacy",
            "layer_ids": ["layer-1"],
            "job_id": "",
            "image_index": 0,
            "seed": 123,
            "params_snapshot": {},
            "group_id": "group-1",
            "group_name": "[0001] - legacy",
            "job_id_short": "",
            "sync_index": 1,
        }
    )

    assert record.manual_label == ""
