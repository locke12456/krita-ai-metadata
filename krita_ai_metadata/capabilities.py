from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import ai_diffusion_compat


MISSING_AI_IMPORT_WARNING = ""
MISSING_ACTIVE_MODEL_WARNING = ""


class RuntimeMode(str, Enum):
    ai_enabled = "ai_enabled"
    manual_only = "manual_only"


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    mode: RuntimeMode
    mode_label: str
    mode_warning: str
    ai_diffusion_available: bool
    active_ai_model_available: bool
    prompt_search_enabled: bool
    ai_metadata_enabled: bool
    manual_group_enabled: bool
    basic_export_enabled: bool


_CURRENT_FLAGS: FeatureFlags | None = None


def build_feature_flags() -> FeatureFlags:
    ai_available = ai_diffusion_compat.IMPORT_ERROR is None
    active_model_available = False
    warning = ""

    if not ai_available:
        warning = MISSING_AI_IMPORT_WARNING
    else:
        try:
            active_model_available = ai_diffusion_compat.active_model() is not None
        except Exception:
            active_model_available = False

        if not active_model_available:
            warning = MISSING_ACTIVE_MODEL_WARNING

    ai_enabled = ai_available and active_model_available

    if ai_enabled:
        return FeatureFlags(
            mode=RuntimeMode.ai_enabled,
            mode_label="AI-enabled",
            mode_warning="",
            ai_diffusion_available=True,
            active_ai_model_available=True,
            prompt_search_enabled=True,
            ai_metadata_enabled=True,
            manual_group_enabled=True,
            basic_export_enabled=True,
        )

    return FeatureFlags(
        mode=RuntimeMode.manual_only,
        mode_label="Manual metadata export",
        mode_warning="",
        ai_diffusion_available=ai_available,
        active_ai_model_available=active_model_available,
        prompt_search_enabled=False,
        ai_metadata_enabled=False,
        manual_group_enabled=True,
        basic_export_enabled=True,
    )


def refresh_feature_flags() -> FeatureFlags:
    global _CURRENT_FLAGS
    _CURRENT_FLAGS = build_feature_flags()
    return _CURRENT_FLAGS


def current_feature_flags() -> FeatureFlags:
    global _CURRENT_FLAGS
    if _CURRENT_FLAGS is None:
        _CURRENT_FLAGS = build_feature_flags()
    return _CURRENT_FLAGS