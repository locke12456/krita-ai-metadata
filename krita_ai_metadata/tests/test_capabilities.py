from __future__ import annotations

from krita_ai_metadata import ai_diffusion_compat
from krita_ai_metadata.capabilities import (
    MISSING_ACTIVE_MODEL_WARNING,
    MISSING_AI_IMPORT_WARNING,
    RuntimeMode,
    build_feature_flags,
)


def test_manual_only_when_ai_import_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "IMPORT_ERROR", ImportError("missing"))

    flags = build_feature_flags()

    assert flags.mode == RuntimeMode.manual_only
    assert flags.mode_warning == MISSING_AI_IMPORT_WARNING
    assert flags.prompt_search_enabled is False
    assert flags.ai_metadata_enabled is False
    assert flags.manual_group_enabled is True
    assert flags.basic_export_enabled is True


def test_manual_only_when_active_model_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "IMPORT_ERROR", None)
    monkeypatch.setattr(ai_diffusion_compat, "active_model", lambda: None)

    flags = build_feature_flags()

    assert flags.mode == RuntimeMode.manual_only
    assert flags.mode_warning == MISSING_ACTIVE_MODEL_WARNING
    assert flags.prompt_search_enabled is False


def test_ai_enabled_when_active_model_exists(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "IMPORT_ERROR", None)
    monkeypatch.setattr(ai_diffusion_compat, "active_model", lambda: object())

    flags = build_feature_flags()

    assert flags.mode == RuntimeMode.ai_enabled
    assert flags.mode_label == "AI-enabled"
    assert flags.prompt_search_enabled is True
    assert flags.ai_metadata_enabled is True
