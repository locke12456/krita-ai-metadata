from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from ai_diffusion.image import Bounds
from ai_diffusion.jobs import JobParams, JobRegion


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Bounds):
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
    def serialize_job_params(self, params: JobParams) -> dict[str, Any]:
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

    def serialize_job_region(self, region: JobRegion) -> dict[str, Any]:
        return {
            "layer_id": region.layer_id,
            "prompt": region.prompt,
            "bounds": _serialize_value(region.bounds),
            "is_background": region.is_background,
        }

    def deserialize_job_params(self, data: dict[str, Any]) -> JobParams:
        restored = dict(data)
        if isinstance(restored.get("frame"), list):
            restored["frame"] = tuple(restored["frame"])
        restored.pop("inpaint_mode", None)
        return JobParams.from_dict(restored)