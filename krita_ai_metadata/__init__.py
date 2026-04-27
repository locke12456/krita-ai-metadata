from __future__ import annotations

from krita import Krita

from .extension import KritaAIMetadataExtension


Krita.instance().addExtension(KritaAIMetadataExtension(Krita.instance()))
