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


def _dock_right_position():
    """Resolve Krita 5/6 compatible docker right-side position."""
    if DockWidgetFactoryBase is None:
        return None

    direct = getattr(DockWidgetFactoryBase, "DockRight", None)
    if direct is not None:
        return direct

    for container_name in ("DockPosition", "DockWidgetArea"):
        container = getattr(DockWidgetFactoryBase, container_name, None)
        if container is None:
            continue
        for member_name in ("DockRight", "RightDockWidgetArea", "RightDockWidget"):
            value = getattr(container, member_name, None)
            if value is not None:
                return value

    return None


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
        try:
            from .extension import KritaAIMetadataExtension
        except Exception:
            KritaAIMetadataExtension = None

        if KritaAIMetadataExtension is not None:
            app.addExtension(KritaAIMetadataExtension(app))

    if hasattr(app, "addDockWidgetFactory"):
        try:
            from .docker import KritaAIMetadataExportDocker
        except Exception:
            return

        dock_right = _dock_right_position()
        if dock_right is None:
            return

        app.addDockWidgetFactory(
            DockWidgetFactory(
                "kritaAIMetadataExport",
                dock_right,
                KritaAIMetadataExportDocker,
            )
        )


_register_krita_plugin()
