from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from PyQt5.QtCore import QByteArray

from ai_diffusion.document import Document


ANNOTATION_KEY = "krita_export_sync_map.json"
SCHEMA_VERSION = 1


@dataclass
class SyncRecord:
    target_type: str
    export_key: str
    layer_ids: list[str]
    job_id: str
    image_index: int
    seed: int
    params_snapshot: dict[str, Any]
    group_id: str | None = None
    group_name: str | None = None
    job_id_short: str = ""
    sync_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SyncRecord":
        return SyncRecord(
            target_type=data["target_type"],
            export_key=data["export_key"],
            layer_ids=list(data.get("layer_ids", [])),
            job_id=data.get("job_id", ""),
            image_index=int(data.get("image_index", 0)),
            seed=int(data.get("seed", 0)),
            params_snapshot=dict(data.get("params_snapshot", {})),
            group_id=data.get("group_id"),
            group_name=data.get("group_name"),
            job_id_short=data.get("job_id_short", ""),
            sync_index=int(data.get("sync_index", 0)),
        )


@dataclass
class SyncMapData:
    version: int = SCHEMA_VERSION
    next_sync_index: int = 1
    records_by_layer_id: dict[str, SyncRecord] = field(default_factory=dict)
    records_by_group_id: dict[str, SyncRecord] = field(default_factory=dict)
    records_by_group_name: dict[str, SyncRecord] = field(default_factory=dict)


class SyncMapStore:
    def __init__(self, document: Document, annotation_key: str = ANNOTATION_KEY) -> None:
        self.document = document
        self.annotation_key = annotation_key
        self.data = SyncMapData()
        self.load()

    def load(self) -> None:
        annotation = self.document.find_annotation(self.annotation_key)
        if annotation is None:
            self.data = SyncMapData()
            return
        payload = bytes(annotation).decode("utf-8")
        raw = json.loads(payload)
        self.data = SyncMapData(
            version=int(raw.get("version", SCHEMA_VERSION)),
            next_sync_index=int(raw.get("next_sync_index", 1)),
        )
        for layer_id, record in raw.get("records_by_layer_id", {}).items():
            self.data.records_by_layer_id[layer_id] = SyncRecord.from_dict(record)
        for group_id, record in raw.get("records_by_group_id", {}).items():
            self.data.records_by_group_id[group_id] = SyncRecord.from_dict(record)
        for group_name, record in raw.get("records_by_group_name", {}).items():
            self.data.records_by_group_name[group_name] = SyncRecord.from_dict(record)

    def save(self) -> None:
        raw = {
            "version": self.data.version,
            "next_sync_index": self.data.next_sync_index,
            "records_by_layer_id": {
                key: record.to_dict() for key, record in self.data.records_by_layer_id.items()
            },
            "records_by_group_id": {
                key: record.to_dict() for key, record in self.data.records_by_group_id.items()
            },
            "records_by_group_name": {
                key: record.to_dict() for key, record in self.data.records_by_group_name.items()
            },
        }
        payload = json.dumps(raw, indent=2, ensure_ascii=False).encode("utf-8")
        self.document.annotate(self.annotation_key, QByteArray(payload))

    def allocate_sync_index(self) -> int:
        value = self.data.next_sync_index
        self.data.next_sync_index += 1
        return value

    def record_apply(self, record: SyncRecord) -> SyncRecord:
        if record.sync_index <= 0:
            record.sync_index = self.allocate_sync_index()
        for layer_id in record.layer_ids:
            self.data.records_by_layer_id[layer_id] = record
        if record.target_type == "group":
            if record.group_id:
                self.data.records_by_group_id[record.group_id] = record
            if record.group_name:
                self.data.records_by_group_name[record.group_name] = record
        self.save()
        return record

    def resolve_layer(self, layer_id: str) -> SyncRecord | None:
        return self.data.records_by_layer_id.get(layer_id)

    def resolve_group(self, group_id: str | None = None, group_name: str | None = None) -> SyncRecord | None:
        if group_id and group_id in self.data.records_by_group_id:
            return self.data.records_by_group_id[group_id]
        if group_name and group_name in self.data.records_by_group_name:
            return self.data.records_by_group_name[group_name]
        return None

    def all_records(self) -> list[SyncRecord]:
        seen: set[int] = set()
        records: list[SyncRecord] = []
        for record in list(self.data.records_by_layer_id.values()) + list(self.data.records_by_group_id.values()):
            marker = id(record)
            if marker not in seen:
                seen.add(marker)
                records.append(record)
        records.sort(key=lambda item: item.sync_index)
        return records