from __future__ import annotations

import importlib
import sys
import types

import pytest


def _clear_ai_modules(monkeypatch) -> None:
    for name in (
        "krita_ai_metadata.ai_diffusion_compat",
        "ai_diffusion",
        "ai_diffusion.document",
        "ai_diffusion.image",
        "ai_diffusion.jobs",
        "ai_diffusion.layer",
        "ai_diffusion.root",
        "ai_diffusion.text",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)

    import krita_ai_metadata

    if hasattr(krita_ai_metadata, "ai_diffusion_compat"):
        delattr(krita_ai_metadata, "ai_diffusion_compat")


def _install_successful_ai_modules(monkeypatch) -> None:
    package = types.ModuleType("ai_diffusion")
    package.__path__ = []
    monkeypatch.setitem(sys.modules, "ai_diffusion", package)

    document_mod = types.ModuleType("ai_diffusion.document")

    class Document:
        pass

    class KritaDocument:
        @staticmethod
        def active():
            return "active-document"

        @staticmethod
        def active_instance():
            return "active-instance"

    document_mod.Document = Document
    document_mod.KritaDocument = KritaDocument
    monkeypatch.setitem(sys.modules, "ai_diffusion.document", document_mod)

    image_mod = types.ModuleType("ai_diffusion.image")

    class Bounds:
        def __init__(self, x, y, width, height):
            self.x = x
            self.y = y
            self.width = width
            self.height = height

    class Image:
        pass

    image_mod.Bounds = Bounds
    image_mod.Image = Image
    monkeypatch.setitem(sys.modules, "ai_diffusion.image", image_mod)

    jobs_mod = types.ModuleType("ai_diffusion.jobs")

    class JobParams:
        @staticmethod
        def from_dict(data):
            return {"params": dict(data)}

    class JobRegion:
        pass

    class JobState:
        finished = object()

    jobs_mod.JobParams = JobParams
    jobs_mod.JobRegion = JobRegion
    jobs_mod.JobState = JobState
    monkeypatch.setitem(sys.modules, "ai_diffusion.jobs", jobs_mod)

    layer_mod = types.ModuleType("ai_diffusion.layer")

    class Layer:
        pass

    class LayerManager:
        pass

    class LayerType:
        group = object()

    class RestoreActiveLayer:
        pass

    layer_mod.Layer = Layer
    layer_mod.LayerManager = LayerManager
    layer_mod.LayerType = LayerType
    layer_mod.RestoreActiveLayer = RestoreActiveLayer
    monkeypatch.setitem(sys.modules, "ai_diffusion.layer", layer_mod)

    root_mod = types.ModuleType("ai_diffusion.root")

    class Root:
        def model_for_active_document(self):
            return "active-model"

    root_mod.root = Root()
    monkeypatch.setitem(sys.modules, "ai_diffusion.root", root_mod)

    text_mod = types.ModuleType("ai_diffusion.text")
    text_mod.create_img_metadata = lambda params: f"formatted:{params!r}"
    monkeypatch.setitem(sys.modules, "ai_diffusion.text", text_mod)


def _install_failed_ai_package(monkeypatch) -> None:
    package = types.ModuleType("ai_diffusion")
    package.__path__ = []
    monkeypatch.setitem(sys.modules, "ai_diffusion", package)


def _import_ai_compat_fresh(monkeypatch):
    _clear_ai_modules(monkeypatch)
    return importlib.import_module("krita_ai_metadata.ai_diffusion_compat")


def test_ai_diffusion_compat_binds_optional_api_when_imports_succeed(monkeypatch) -> None:
    _clear_ai_modules(monkeypatch)
    _install_successful_ai_modules(monkeypatch)

    ai_diffusion_compat = importlib.import_module("krita_ai_metadata.ai_diffusion_compat")

    assert ai_diffusion_compat.IMPORT_ERROR is None
    assert ai_diffusion_compat.require_api() is None
    assert ai_diffusion_compat.active_document() == "active-document"
    assert ai_diffusion_compat.active_document_instance() == "active-instance"
    assert ai_diffusion_compat.active_model() == "active-model"
    assert ai_diffusion_compat.deserialize_job_params({"seed": 1}) == {"params": {"seed": 1}}
    assert ai_diffusion_compat.format_img_metadata({"seed": 1}) == "formatted:{'seed': 1}"


def test_ai_diffusion_compat_exposes_unavailable_state_when_imports_fail(monkeypatch) -> None:
    _clear_ai_modules(monkeypatch)
    _install_failed_ai_package(monkeypatch)

    ai_diffusion_compat = importlib.import_module("krita_ai_metadata.ai_diffusion_compat")

    assert ai_diffusion_compat.IMPORT_ERROR is not None
    with pytest.raises(RuntimeError, match="Krita AI Diffusion API unavailable"):
        ai_diffusion_compat.require_api()


def test_trim_prompt_shortens_long_text(monkeypatch) -> None:
    ai_diffusion_compat = _import_ai_compat_fresh(monkeypatch)

    assert ai_diffusion_compat.trim_prompt("abcdef", 5) == "ab..."
    assert ai_diffusion_compat.trim_prompt("abc", 5) == "abc"


def test_wrapper_helper_functions_after_successful_import(monkeypatch) -> None:
    _clear_ai_modules(monkeypatch)
    _install_successful_ai_modules(monkeypatch)
    ai_diffusion_compat = importlib.import_module("krita_ai_metadata.ai_diffusion_compat")

    class FakeJob:
        state = ai_diffusion_compat.JobState.finished

    class FakeGroupLayer:
        type = ai_diffusion_compat.LayerType.group

    class FakeImageType:
        is_image = True

    class FakeImageLayer:
        type = FakeImageType()

    class FakeStringGroupLayer:
        type = "grouplayer"

    class FakeStringPaintLayer:
        type = "paintlayer"

    assert ai_diffusion_compat.is_finished_job(FakeJob()) is True
    assert ai_diffusion_compat.is_group_layer(FakeGroupLayer()) is True
    assert ai_diffusion_compat.is_image_layer(FakeImageLayer()) is True
    assert ai_diffusion_compat.is_group_layer(FakeStringGroupLayer()) is True
    assert ai_diffusion_compat.is_image_layer(FakeStringPaintLayer()) is True
