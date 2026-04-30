from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .ai_diffusion_compat import deserialize_job_params as compat_deserialize_job_params


def _build_jobparams_fields() -> set[str]:
    """Return the set of valid JobParams dataclass field names.
    Uses dynamic introspection when ai_diffusion is available,
    falls back to a hardcoded set otherwise.
    """
    _FALLBACK = {
        "bounds", "name", "regions", "metadata", "seed",
        "has_mask", "is_layered", "inpaint_mode", "frame",
        "animation_id", "resize_canvas",
    }
    try:
        from dataclasses import fields as dc_fields
        from ai_diffusion.jobs import JobParams
        return {f.name for f in dc_fields(JobParams)}
    except Exception:
        return _FALLBACK


_JOBPARAMS_FIELDS: set[str] = _build_jobparams_fields()


def _serialize_value(value: Any) -> Any:
    if all(hasattr(value, attr) for attr in ("x", "y", "width", "height")):
        return [value.x, value.y, value.width, value.height]
    if isinstance(value, Enum):
        return value.name
    if is_dataclass(value):
        return {key: _serialize_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return value


class JobParamsSerializer:
    def serialize_job_params(self, params: Any) -> dict[str, Any]:
        data = {
            "bounds": _serialize_value(params.bounds),
            "name": params.name,
            "regions": [self.serialize_job_region(region) for region in params.regions],
            "metadata": _serialize_value(params.metadata),
            "seed": params.seed,
            "has_mask": params.has_mask,
            "is_layered": params.is_layered,
            "inpaint_mode": _serialize_value(getattr(params, "inpaint_mode", None)),
            "frame": list(params.frame),
            "animation_id": params.animation_id,
            "resize_canvas": params.resize_canvas,
        }
        return data

    def serialize_job_region(self, region: Any) -> dict[str, Any]:
        return {
            "layer_id": region.layer_id,
            "prompt": region.prompt,
            "bounds": _serialize_value(region.bounds),
            "is_background": region.is_background,
        }

    def deserialize_job_params(self, data: dict[str, Any]) -> Any:
        restored = dict(data)
        # Defensive: strip keys not in JobParams dataclass to prevent TypeError
        restored = {k: v for k, v in restored.items() if k in _JOBPARAMS_FIELDS}
        if isinstance(restored.get("frame"), list):
            restored["frame"] = tuple(restored["frame"])
        restored.pop("inpaint_mode", None)
        return compat_deserialize_job_params(restored)
