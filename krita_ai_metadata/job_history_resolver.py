from __future__ import annotations

from typing import Any

from .ai_diffusion_compat import active_model, is_finished_job, trim_prompt
from .job_params_serializer import JobParamsSerializer


class JobHistoryResolver:
    """Resolve JobParams from Krita AI Diffusion's active model job history."""

    def __init__(self, serializer: JobParamsSerializer | None = None) -> None:
        self.serializer = serializer or JobParamsSerializer()

    def params_snapshot_for_layers(self, layers: list[Any]) -> dict[str, Any]:
        params = self.params_for_layers(layers)
        if params is None:
            return {}
        return self.serializer.serialize_job_params(params)

    def params_for_layers(self, layers: list[Any]):
        jobs = self._jobs_newest_first()
        if not jobs:
            return None

        names = [layer.name for layer in layers if layer.name]

        for job in jobs:
            params = getattr(job, "params", None)
            if params is not None and self._matches_names(params, names):
                return params

        return None

    def _jobs_newest_first(self):
        try:
            model = active_model()
        except Exception:
            return []
        if model is None:
            return []

        jobs = list(getattr(model, "jobs", []))
        finished = [job for job in jobs if is_finished_job(job)]
        return list(reversed(finished or jobs))

    def _matches_names(self, params, names: list[str]) -> bool:
        seed = str(getattr(params, "seed", "") or "")
        if not seed or seed == "0":
            return False

        expected_names = self._expected_layer_names(params, seed)
        for name in names:
            if name in expected_names:
                return True
            if self._has_seed_suffix(name, seed) and self._layer_prompt(name, seed) in self._expected_prompts(params):
                return True

        return False

    def _expected_layer_names(self, params, seed: str) -> set[str]:
        """Return layer names created by ai_diffusion.model.Model.apply_result."""
        prompts = self._expected_prompts(params)
        result: set[str] = set()

        for prompt in prompts:
            result.add(f"[Generated] {prompt} ({seed})")
            result.add(f"{prompt} ({seed})")
            result.add(f"[Upscale] {prompt} ({seed})")

        if getattr(params, "is_layered", False):
            base_prompt = trim_prompt(str(getattr(params, "name", "") or ""), 200)
            for index in range(1, 17):
                result.add(f"[Layer {index}] {base_prompt} ({seed})")

        return result

    def _expected_prompts(self, params) -> set[str]:
        """Return prompt text used by normal and region result layer creation."""
        prompts: set[str] = set()
        prompt_name = str(getattr(params, "name", "") or "")
        if prompt_name:
            prompts.add(trim_prompt(prompt_name, 200))

        for region in getattr(params, "regions", []) or []:
            region_prompt = str(getattr(region, "prompt", "") or "")
            if region_prompt:
                prompts.add(region_prompt)

        return prompts

    def _has_seed_suffix(self, layer_name: str, seed: str) -> bool:
        """Return True when a layer name ends with the Krita AI Diffusion seed suffix."""
        return layer_name.strip().endswith(f"({seed})")

    def _layer_prompt(self, layer_name: str, seed: str) -> str:
        """Remove apply_result prefixes and the seed suffix from a layer name."""
        text = layer_name.strip()
        suffix = f" ({seed})"
        if text.endswith(suffix):
            text = text[: -len(suffix)]

        for prefix in ("[Generated] ", "[Upscale] "):
            if text.startswith(prefix):
                return text[len(prefix) :].strip()

        if text.startswith("[Layer "):
            end = text.find("] ")
            if end >= 0:
                return text[end + 2 :].strip()

        return text.strip()
