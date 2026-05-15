from __future__ import annotations

import re
import sys
from typing import Any

from .ai_diffusion_compat import active_model, is_finished_job, trim_prompt
from .job_params_serializer import JobParamsSerializer


class JobHistoryResolver:
    """Resolve JobParams from Krita AI Diffusion's active model job history."""

    def __init__(self, serializer: JobParamsSerializer | None = None) -> None:
        self.serializer = serializer or JobParamsSerializer()

    def _log(self, msg: str) -> None:
        print(f"[job_history_resolver] {msg}", file=sys.stderr, flush=True)

    def params_snapshot_for_layers(self, layers: list[Any]) -> dict[str, Any]:
        params = self.params_for_layers(layers)
        if params is None:
            return {}
        return self.serializer.serialize_job_params(params)

    def params_for_layers(self, layers: list[Any]):
        jobs = self._jobs_newest_first()
        if not jobs:
            self._log("no jobs available")
            return None

        names = [layer.name for layer in layers if layer.name]
        self._log(f"lookup names={names!r} jobs={len(jobs)}")

        for job in jobs:
            params = getattr(job, "params", None)
            if params is not None and self._matches_names(params, names):
                self._log(
                    f"matched seed={getattr(params, 'seed', '')!r} "
                    f"name={getattr(params, 'name', '')!r}"
                )
                return params

        self._log(f"no match names={names!r}")
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
        expected_prompts = self._expected_prompts(params)

        for name in names:
            if name in expected_names:
                return True
            if not self._has_seed_suffix(name, seed):
                continue

            layer_prompt = self._layer_prompt(name, seed)
            if any(self._prompt_matches(layer_prompt, expected) for expected in expected_prompts):
                return True

        return False

    def _expected_layer_names(self, params, seed: str) -> set[str]:
        """Return layer names created by ai_diffusion.model.Model.apply_result."""
        prompts = self._expected_prompts(params)
        result: set[str] = set()

        for prompt in prompts:
            layer_text = self._ai_diffusion_trim_text(prompt, 200)
            result.add(f"[Generated] {layer_text} ({seed})")
            result.add(f"{prompt} ({seed})")
            result.add(f"[Upscale] {layer_text} ({seed})")

        if getattr(params, "is_layered", False):
            base_prompt = self._ai_diffusion_trim_text(str(getattr(params, "name", "") or ""), 200)
            for index in range(1, 17):
                result.add(f"[Layer {index}] {base_prompt} ({seed})")

        return result

    def _expected_prompts(self, params) -> set[str]:
        """Return prompt text used by normal and region result layer creation."""
        prompts: set[str] = set()
        prompt_name = str(getattr(params, "name", "") or "")
        if prompt_name:
            prompts.add(prompt_name)

        for region in getattr(params, "regions", []) or []:
            region_prompt = str(getattr(region, "prompt", "") or "")
            if region_prompt:
                prompts.add(region_prompt)

        return prompts

    def _has_seed_suffix(self, layer_name: str, seed: str) -> bool:
        """Return True when a layer name ends with the Krita AI Diffusion seed suffix."""
        return layer_name.strip().endswith(f"({seed})")

    def _layer_prompt(self, layer_name: str, seed: str) -> str:
        """Remove apply_result prefixes, export prefixes, and the seed suffix."""
        text = layer_name.strip()
        suffix = f" ({seed})"
        if text.endswith(suffix):
            text = text[: -len(suffix)]

        text = self._strip_export_prefix(text)

        for prefix in ("[Generated] ", "[Upscale] "):
            if text.startswith(prefix):
                return self._strip_export_prefix(text[len(prefix) :]).strip()

        if text.startswith("[Layer "):
            end = text.find("] ")
            if end >= 0:
                return self._strip_export_prefix(text[end + 2 :]).strip()

        return self._strip_export_prefix(text).strip()

    def _strip_export_prefix(self, text: str) -> str:
        """Remove export index prefixes such as '[0007] - ' from layer names."""
        return re.sub(r"^\[\d+\]\s*-\s*", "", text).strip()

    def _normalize_prompt_text(self, text: str) -> str:
        """Normalize prompt text for robust history matching."""
        return " ".join(self._strip_export_prefix(str(text or "")).split()).strip()

    def _ai_diffusion_trim_text(self, text: str, max_length: int) -> str:
        """Mirror ai_diffusion.util.trim_text for layer names."""
        text = str(text or "")
        if len(text) > max_length:
            return text[: max_length - 3] + "..."
        return text

    def _prompt_matches(self, layer_prompt: str, expected_prompt: str) -> bool:
        """Return True when a layer prompt matches a full or trimmed history prompt."""
        layer = self._normalize_prompt_text(layer_prompt)
        expected = self._normalize_prompt_text(expected_prompt)
        if not layer or not expected:
            return False
        if layer == expected:
            return True

        trimmed = self._normalize_prompt_text(self._ai_diffusion_trim_text(expected, 200))
        if layer == trimmed:
            return True

        if "..." in layer:
            return self._ellipsis_prompt_matches(layer, expected)

        return layer in expected or expected in layer

    def _ellipsis_prompt_matches(self, layer_prompt: str, expected_prompt: str) -> bool:
        """Match prompts that were shortened with an ellipsis in the layer name."""
        parts = [part.strip() for part in layer_prompt.split("...") if part.strip()]
        if not parts:
            return False

        position = 0
        for part in parts:
            index = expected_prompt.find(part, position)
            if index < 0:
                return False
            position = index + len(part)

        if layer_prompt.endswith("..."):
            return expected_prompt.startswith(parts[0])
        if layer_prompt.startswith("..."):
            return expected_prompt.endswith(parts[-1])
        return True
