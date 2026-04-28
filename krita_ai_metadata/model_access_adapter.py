from __future__ import annotations

from typing import Any

from .ai_diffusion_compat import active_document_instance


class ModelAccessAdapter:
    def __init__(self, model_provider: Any | None = None) -> None:
        self._model_provider = model_provider

    def active_model(self) -> Any | None:
        if self._model_provider is None:
            return None
        model = self._model_provider() if callable(self._model_provider) else self._model_provider
        if model is None:
            return None
        document = getattr(model, "document", None)
        if document is None:
            return None
        try:
            active_document = active_document_instance()
        except Exception:
            active_document = None
        if active_document is not None and document != active_document:
            return None
        if not hasattr(model, "apply_generated_result"):
            return None
        if not hasattr(model, "jobs"):
            return None
        if not hasattr(model, "layers"):
            return None
        return model