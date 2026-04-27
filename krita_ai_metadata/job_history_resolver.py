from __future__ import annotations

from typing import Any

from ai_diffusion.jobs import JobState
from ai_diffusion.layer import Layer
from ai_diffusion.root import root

from .job_params_serializer import JobParamsSerializer


class JobHistoryResolver:
    """Resolve JobParams from Krita AI Diffusion's active model job history."""

    def __init__(self, serializer: JobParamsSerializer | None = None) -> None:
        self.serializer = serializer or JobParamsSerializer()

    def params_snapshot_for_layers(self, layers: list[Layer]) -> dict[str, Any]:
        params = self.params_for_layers(layers)
        if params is None:
            return {}
        return self.serializer.serialize_job_params(params)

    def params_for_layers(self, layers: list[Layer]):
        jobs = self._jobs_newest_first()
        if not jobs:
            return None

        names = [layer.name for layer in layers]

        for job in jobs:
            params = getattr(job, "params", None)
            if params is not None and self._matches_names(params, names):
                return params

        for job in jobs:
            if self._was_used(job):
                return getattr(job, "params", None)

        return getattr(jobs[0], "params", None)

    def _jobs_newest_first(self):
        try:
            model = root.model_for_active_document()
        except Exception:
            return []
        if model is None:
            return []

        jobs = list(getattr(model, "jobs", []))
        finished = [job for job in jobs if getattr(job, "state", None) is JobState.finished]
        return list(reversed(finished or jobs))

    def _matches_names(self, params, names: list[str]) -> bool:
        seed = str(getattr(params, "seed", ""))
        prompt_name = str(getattr(params, "name", "") or "")
        prompt_short = prompt_name[:80]

        for name in names:
            if seed and seed != "0" and seed in name:
                return True
            if prompt_short and prompt_short in name:
                return True
            if prompt_name and name in prompt_name:
                return True
        return False

    def _was_used(self, job) -> bool:
        in_use = getattr(job, "in_use", {})
        try:
            return any(bool(value) for value in in_use.values())
        except Exception:
            return False
