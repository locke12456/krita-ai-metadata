from __future__ import annotations

import pytest

from krita_ai_metadata import ai_diffusion_compat


def test_trim_prompt_shortens_long_text() -> None:
    assert ai_diffusion_compat.trim_prompt("abcdef", 5) == "ab..."
    assert ai_diffusion_compat.trim_prompt("abc", 5) == "abc"


def test_require_api_success_when_import_error_is_absent(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "IMPORT_ERROR", None)

    assert ai_diffusion_compat.require_api() is None


def test_require_api_raises_when_import_error_is_set(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "IMPORT_ERROR", ImportError("missing"))

    with pytest.raises(RuntimeError, match="Krita AI Diffusion API unavailable"):
        ai_diffusion_compat.require_api()


def test_active_model_returns_none_without_root(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "IMPORT_ERROR", None)
    monkeypatch.setattr(ai_diffusion_compat, "root", None)

    assert ai_diffusion_compat.active_model() is None

def test_wrapper_helper_functions(monkeypatch) -> None:
    class FakeState:
        finished = object()

    class FakeLayerType:
        group = object()

    class FakeJob:
        state = FakeState.finished

    class FakeGroupLayer:
        type = FakeLayerType.group

    class FakeImageType:
        is_image = True

    class FakeImageLayer:
        type = FakeImageType()

    monkeypatch.setattr(ai_diffusion_compat, "JobState", FakeState)
    monkeypatch.setattr(ai_diffusion_compat, "LayerType", FakeLayerType)

    assert ai_diffusion_compat.is_finished_job(FakeJob()) is True
    assert ai_diffusion_compat.is_group_layer(FakeGroupLayer()) is True
    assert ai_diffusion_compat.is_image_layer(FakeImageLayer()) is True


def test_format_img_metadata_uses_wrapper_formatter(monkeypatch) -> None:
    monkeypatch.setattr(ai_diffusion_compat, "IMPORT_ERROR", None)
    monkeypatch.setattr(ai_diffusion_compat, "create_img_metadata", lambda params: "formatted")

    assert ai_diffusion_compat.format_img_metadata(object()) == "formatted"

