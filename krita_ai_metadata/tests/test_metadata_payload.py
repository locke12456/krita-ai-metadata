from __future__ import annotations

from dataclasses import dataclass, field

from krita_export_plugin.export_target_scanner import ExportTarget
from krita_export_plugin.metadata_resolver import MetadataResolver


@dataclass
class FakeBounds:
    is_zero: bool = False


@dataclass
class FakeType:
    value: str = "grouplayer"


@dataclass
class FakeLayer:
    id_string: str = "{layer-1}"
    name: str = "Layer 1"
    bounds: FakeBounds = field(default_factory=FakeBounds)
    child_layers: list = field(default_factory=list)
    type: FakeType = field(default_factory=FakeType)
    is_visible: bool = True


def test_metadata_resolver_builds_sidecar_payload():
    target = ExportTarget(
        layer=FakeLayer(),
        target_type="group",
        key="0001-job-seed",
        record={
            "target_type": "group",
            "export_key": "0001-job-seed",
            "layer_ids": ["{layer-1}"],
            "group_id": "{group-1}",
            "group_name": "[0001] - job - seed",
            "job_id": "job-id",
            "job_id_short": "job-id",
            "image_index": 0,
            "seed": 123,
            "params_snapshot": {
                "bounds": [0, 0, 512, 768],
                "name": "prompt",
                "regions": [],
                "metadata": {
                    "prompt": "cat",
                    "negative_prompt": "bad",
                    "sampler": "Euler",
                    "steps": 20,
                    "guidance": 7.0,
                    "checkpoint": "model",
                },
                "seed": 123,
                "has_mask": False,
                "is_layered": False,
                "frame": [0, 0, 0],
                "animation_id": "",
                "resize_canvas": False,
            },
        },
    )

    metadata = MetadataResolver().resolve(target)

    assert metadata.has_metadata
    assert "cat" in metadata.a1111_parameters
    assert metadata.payload["key"] == "0001-job-seed"
    assert metadata.payload["seed"] == 123
    assert metadata.payload["layer_ids"] == ["{layer-1}"]
    assert metadata.payload["metadata_inherited"] is False


def test_metadata_resolver_reports_missing_snapshot():
    target = ExportTarget(
        layer=FakeLayer(),
        target_type="layer",
        key="unresolved",
        record={"target_type": "layer", "export_key": "unresolved"},
    )

    metadata = MetadataResolver().resolve(target)

    assert not metadata.has_metadata
    assert metadata.warnings
    assert "params_snapshot" in metadata.warnings[0]


def test_metadata_resolver_marks_inherited_payload():
    target = ExportTarget(
        layer=FakeLayer(),
        target_type="group",
        key="0001-job-seed",
        record={
            "target_type": "group",
            "export_key": "0001-job-seed",
            "params_snapshot": {
                "bounds": [0, 0, 512, 768],
                "name": "prompt",
                "regions": [],
                "metadata": {"prompt": "cat"},
                "seed": 123,
                "has_mask": False,
                "is_layered": False,
                "frame": [0, 0, 0],
                "animation_id": "",
                "resize_canvas": False,
            },
        },
        warnings=["Metadata for layer 'Layer 1' inherited from parent group 'Group 1'."],
    )

    metadata = MetadataResolver().resolve(target)

    assert metadata.payload["metadata_inherited"] is True
    assert any("inherited from parent group" in warning for warning in metadata.warnings)
