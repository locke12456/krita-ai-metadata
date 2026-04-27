from __future__ import annotations

# Package import must remain safe in local pytest runs where Krita's embedded
# Python API is replaced by a lightweight stub. Runtime registration still
# happens when the real Krita module exposes the required APIs.
try:
    from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita
except Exception:  # pragma: no cover - exercised by local test stubs
    DockWidgetFactory = None
    DockWidgetFactoryBase = None
    Krita = None

from .extension import KritaAIMetadataExtension


def _register_krita_plugin() -> None:
    if Krita is None or DockWidgetFactory is None or DockWidgetFactoryBase is None:
        return

    try:
        app = Krita.instance()
    except Exception:
        return

    if app is None:
        return

    if hasattr(app, "addExtension"):
        app.addExtension(KritaAIMetadataExtension(app))

    if hasattr(app, "addDockWidgetFactory"):
        try:
            from .docker import KritaAIMetadataExportDocker
        except Exception:
            return

        app.addDockWidgetFactory(
            DockWidgetFactory(
                "kritaAIMetadataExport",
                DockWidgetFactoryBase.DockRight,
                KritaAIMetadataExportDocker,
            )
        )


_register_krita_plugin()
