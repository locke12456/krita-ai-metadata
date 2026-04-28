from __future__ import annotations

from dataclasses import dataclass, field

from krita_ai_metadata.capabilities import FeatureFlags, RuntimeMode
from krita_ai_metadata.export_target_scanner import ExportTarget
from krita_ai_metadata.metadata_resolver import MetadataResolver


@dataclass
class FakeBounds:
    is_zero: bool = False


@dataclass
class FakeType:
    value: str = "paintlayer"
    is_image: bool = True


@dataclass
class FakeLayer:
    id_string: str = "{layer-1}"
    name: str = "Layer 1"
    bounds: FakeBounds = field(default_factory=FakeBounds)
    child_layers: list = field(default_factory=list)
    type: FakeType = field(default_factory=FakeType)
    is_visible: bool = True


def test_metadata_resolver_emits_manual_only_mode_fields() -> None:
    flags = FeatureFlags(
        mode=RuntimeMode.manual_only,
        mode_label="Manual-only (Krita AI Diffusion unavailable)",
        mode_warning="Krita AI Diffusion unavailable; prompt search disabled.",
        ai_diffusion_available=False,
        active_ai_model_available=False,
        prompt_search_enabled=False,
        ai_metadata_enabled=False,
        manual_group_enabled=True,
        basic_export_enabled=True,
    )
    target = ExportTarget(
        layer=FakeLayer(),
        target_type="layer",
        key="manual-layer",
        record=None,
    )

    metadata = MetadataResolver(feature_flags=flags).resolve(target)

    assert metadata.has_metadata is False
    assert metadata.payload["mode"] == "manual_only"
    assert metadata.payload["mode_label"] == "Manual-only (Krita AI Diffusion unavailable)"
    assert metadata.payload["ai_metadata_available"] is False
    assert metadata.payload["prompt_search_enabled"] is False
    assert metadata.payload["mode_warning"] == "Krita AI Diffusion unavailable; prompt search disabled."
    assert "Krita AI Diffusion unavailable; prompt search disabled." in metadata.warnings
