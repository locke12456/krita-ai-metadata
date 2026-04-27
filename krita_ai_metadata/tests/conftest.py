from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


TESTS_DIR = Path(__file__).resolve().parent
PKG_DIR = TESTS_DIR.parent
REPO_ROOT = PKG_DIR.parent


def _add_path(path: Path) -> None:
    text = str(path)
    if path.exists() and text not in sys.path:
        sys.path.insert(0, text)


# Make the real package `krita_ai_metadata` importable.
_add_path(REPO_ROOT)


# Local pytest runs do not provide Krita's embedded `krita` module.
# Adapter tests monkeypatch krita.Krita, so the stub only needs to exist.
if "krita" not in sys.modules:
    krita_stub = types.ModuleType("krita")

    class Krita:
        @staticmethod
        def instance():
            return None

    krita_stub.Krita = Krita
    sys.modules["krita"] = krita_stub


# Do NOT import the real ai_diffusion package during local unit tests.
# Source-only krita-ai-diffusion executes release dependency checks in
# ai_diffusion/__init__.py and fails outside of the plugin bundle.
if "ai_diffusion" not in sys.modules:
    ai_diffusion_pkg = types.ModuleType("ai_diffusion")
    ai_diffusion_pkg.__path__ = []
    sys.modules["ai_diffusion"] = ai_diffusion_pkg


# ---- ai_diffusion.image -------------------------------------------------
image_mod = types.ModuleType("ai_diffusion.image")


@dataclass(frozen=True)
class Bounds:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    @property
    def is_zero(self) -> bool:
        return self.width == 0 or self.height == 0


class Image:
    @staticmethod
    def save_png_with_metadata(filepath: str, metadata_text: str, format: Any = None) -> None:
        Path(filepath).write_bytes(b"")


image_mod.Bounds = Bounds
image_mod.Image = Image
sys.modules["ai_diffusion.image"] = image_mod


# ---- ai_diffusion.jobs --------------------------------------------------
jobs_mod = types.ModuleType("ai_diffusion.jobs")


@dataclass
class JobRegion:
    layer_id: str = ""
    prompt: str = ""
    bounds: Bounds = field(default_factory=Bounds)
    is_background: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobRegion":
        bounds = data.get("bounds", Bounds())
        if isinstance(bounds, (list, tuple)):
            bounds = Bounds(*bounds)
        elif isinstance(bounds, dict):
            bounds = Bounds(**bounds)
        return cls(
            layer_id=data.get("layer_id", ""),
            prompt=data.get("prompt", ""),
            bounds=bounds,
            is_background=bool(data.get("is_background", False)),
        )


@dataclass
class JobParams:
    bounds: Bounds = field(default_factory=Bounds)
    name: str = ""
    regions: list[JobRegion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    has_mask: bool = False
    is_layered: bool = False
    frame: tuple[int, int, int] = (0, 0, 0)
    animation_id: str = ""
    resize_canvas: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobParams":
        bounds = data.get("bounds", Bounds())
        if isinstance(bounds, (list, tuple)):
            bounds = Bounds(*bounds)
        elif isinstance(bounds, dict):
            bounds = Bounds(**bounds)

        regions = [
            item if isinstance(item, JobRegion) else JobRegion.from_dict(item)
            for item in data.get("regions", [])
        ]

        frame = data.get("frame", (0, 0, 0))
        if isinstance(frame, list):
            frame = tuple(frame)

        return cls(
            bounds=bounds,
            name=data.get("name", ""),
            regions=regions,
            metadata=dict(data.get("metadata", {})),
            seed=int(data.get("seed", 0) or 0),
            has_mask=bool(data.get("has_mask", False)),
            is_layered=bool(data.get("is_layered", False)),
            frame=frame,
            animation_id=data.get("animation_id", ""),
            resize_canvas=bool(data.get("resize_canvas", False)),
        )


jobs_mod.JobRegion = JobRegion
jobs_mod.JobParams = JobParams
sys.modules["ai_diffusion.jobs"] = jobs_mod


# ---- ai_diffusion.layer -------------------------------------------------
layer_mod = types.ModuleType("ai_diffusion.layer")


class LayerType(Enum):
    group = "grouplayer"
    paint = "paintlayer"

    @property
    def is_image(self) -> bool:
        return True


class Layer:
    pass


class LayerManager:
    pass


layer_mod.LayerType = LayerType
layer_mod.Layer = Layer
layer_mod.LayerManager = LayerManager
sys.modules["ai_diffusion.layer"] = layer_mod


# ---- ai_diffusion.document ----------------------------------------------
document_mod = types.ModuleType("ai_diffusion.document")


class Document:
    pass


document_mod.Document = Document
sys.modules["ai_diffusion.document"] = document_mod


# ---- ai_diffusion.text --------------------------------------------------
text_mod = types.ModuleType("ai_diffusion.text")


def create_img_metadata(params: JobParams) -> str:
    prompt = params.metadata.get("prompt") or params.name
    negative = params.metadata.get("negative_prompt", "")
    sampler = params.metadata.get("sampler", "")
    steps = params.metadata.get("steps", "")
    guidance = params.metadata.get("guidance", "")
    checkpoint = params.metadata.get("checkpoint", "")

    lines = [str(prompt)]
    if negative:
        lines.append(f"Negative prompt: {negative}")

    fields = []
    if steps != "":
        fields.append(f"Steps: {steps}")
    if sampler:
        fields.append(f"Sampler: {sampler}")
    if guidance != "":
        fields.append(f"CFG scale: {guidance}")
    if params.seed:
        fields.append(f"Seed: {params.seed}")
    if checkpoint:
        fields.append(f"Model: {checkpoint}")

    if fields:
        lines.append(", ".join(fields))

    return "\n".join(lines)


text_mod.create_img_metadata = create_img_metadata
sys.modules["ai_diffusion.text"] = text_mod
