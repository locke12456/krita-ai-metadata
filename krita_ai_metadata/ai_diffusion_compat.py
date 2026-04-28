from __future__ import annotations

from typing import Any


IMPORT_ERROR: Exception | None = None

try:
    from ai_diffusion.document import Document, KritaDocument
    from ai_diffusion.image import Bounds, Image
    from ai_diffusion.jobs import JobParams, JobRegion, JobState
    from ai_diffusion.layer import Layer, LayerManager, LayerType, RestoreActiveLayer
    from ai_diffusion.root import root
    from ai_diffusion.text import create_img_metadata
except Exception as exc:
    IMPORT_ERROR = exc
    Document = Any
    KritaDocument = None
    Bounds = None
    Image = Any
    JobParams = None
    JobRegion = Any
    JobState = None
    Layer = Any
    LayerManager = Any
    LayerType = None
    RestoreActiveLayer = None
    root = None
    create_img_metadata = None


def require_api() -> None:
    if IMPORT_ERROR is not None:
        raise RuntimeError(f"Krita AI Diffusion API unavailable: {IMPORT_ERROR}")


def active_document() -> Any:
    require_api()
    return KritaDocument.active()


def active_document_instance() -> Any:
    require_api()
    return KritaDocument.active_instance()


def active_model() -> Any:
    require_api()
    if root is None:
        return None
    return root.model_for_active_document()


def is_finished_job(job: Any) -> bool:
    if JobState is None:
        return False
    return getattr(job, "state", None) is JobState.finished


def is_group_layer(layer: Any) -> bool:
    layer_type = getattr(layer, "type", None)
    if isinstance(layer_type, str):
        return layer_type.lower() == "grouplayer"
    if LayerType is None:
        return False
    return layer_type is LayerType.group


def is_image_layer(layer: Any) -> bool:
    layer_type = getattr(layer, "type", None)
    if isinstance(layer_type, str):
        return layer_type.lower() in {"paintlayer", "grouplayer", "filelayer", "vectorlayer"}
    return bool(getattr(layer_type, "is_image", False))


def make_bounds(x: int, y: int, width: int, height: int) -> Any:
    require_api()
    return Bounds(x, y, width, height)


def deserialize_job_params(data: dict[str, Any]) -> Any:
    require_api()
    return JobParams.from_dict(data)


def format_img_metadata(params: Any) -> str:
    require_api()
    if create_img_metadata is None:
        return ""
    return create_img_metadata(params)


def trim_prompt(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 3].rstrip() + "..."


def refresh_projection(document: Any) -> None:
    raw_document = getattr(document, "_doc", None)
    if raw_document is None:
        return
    try:
        raw_document.refreshProjection()
    except Exception:
        return