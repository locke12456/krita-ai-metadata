from __future__ import annotations

from ai_diffusion.image import Bounds
from ai_diffusion.jobs import JobParams, JobRegion

from krita_export_plugin.job_params_serializer import JobParamsSerializer


def test_job_params_serializer_roundtrip_through_from_dict():
    serializer = JobParamsSerializer()
    params = JobParams(
        bounds=Bounds(0, 0, 512, 768),
        name="prompt",
        regions=[
            JobRegion(
                layer_id="{layer-1}",
                prompt="region prompt",
                bounds=Bounds(10, 20, 100, 120),
                is_background=False,
            )
        ],
        metadata={
            "prompt": "cat",
            "negative_prompt": "bad",
            "sampler": "Euler",
            "steps": 20,
            "guidance": 7.0,
            "checkpoint": "model",
        },
        seed=123,
        has_mask=True,
        is_layered=False,
        frame=(1, 2, 3),
        animation_id="animation",
        resize_canvas=False,
    )

    snapshot = serializer.serialize_job_params(params)
    restored = serializer.deserialize_job_params(snapshot)

    assert restored.bounds == params.bounds
    assert restored.name == params.name
    assert restored.regions[0].bounds == params.regions[0].bounds
    assert restored.metadata == params.metadata
    assert restored.seed == params.seed
    assert restored.frame == params.frame
