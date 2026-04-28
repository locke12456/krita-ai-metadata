from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def read_source(filename: str) -> str:
    return (PACKAGE_ROOT / filename).read_text(encoding="utf-8")


def test_init_registers_extension_and_docker_factory() -> None:
    source = read_source("__init__.py")

    assert "def _register_krita_plugin()" in source
    assert "app.addExtension(KritaAIMetadataExtension(app))" in source
    assert "app.addDockWidgetFactory(" in source
    assert "DockWidgetFactory(" in source
    assert '"kritaAIMetadataExport"' in source
    assert "def _dock_right_position()" in source
    assert 'getattr(DockWidgetFactoryBase, "DockRight", None)' in source
    assert '"DockPosition"' in source
    assert '"DockWidgetArea"' in source
    assert "KritaAIMetadataExportDocker" in source


def test_extension_keeps_fallback_actions_only() -> None:
    source = read_source("extension.py")

    assert '"krita_ai_metadata_add_group"' in source
    assert '"Add AI Metadata Group..."' in source
    assert '"krita_ai_metadata_export"' in source
    assert '"Export AI Metadata..."' in source
    assert '"krita_ai_metadata_debug_probe"' in source
    assert "MetadataGroupAction().run_from_krita()" in source
    assert "ExportAction().run_from_krita()" in source
    assert "DockWidgetFactory" not in source
    assert "addDockWidgetFactory" not in source


def test_docker_entry_point_exposes_lifecycle_methods() -> None:
    source = read_source("docker.py")

    assert "class KritaAIMetadataExportDocker(DockWidget):" in source
    assert 'self.setWindowTitle("AI Metadata Export")' in source
    assert "self.setWidget(self._window)" in source
    assert "def canvasChanged(self, canvas: krita.Canvas):" in source
    assert "self._window.refresh_from_canvas(canvas)" in source
    assert "def update_content(self):" in source
    assert "self._window.refresh()" in source

def test_runtime_source_uses_compat_wrappers_for_qt_and_ai_imports() -> None:
    allowed = {"qt_compat.py", "ai_diffusion_compat.py"}
    forbidden = ("from PyQt5", "from PyQt6", "import PyQt5", "import PyQt6", "from ai_diffusion.", "import ai_diffusion.")

    for path in PACKAGE_ROOT.rglob("*.py"):
        relative = path.relative_to(PACKAGE_ROOT).as_posix()
        if relative.startswith("tests/") or path.name in allowed:
            continue
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{relative} contains forbidden import marker {marker!r}"


def test_native_krita_api_calls_stay_in_core_adapter() -> None:
    allowed = {"krita_core_adapter.py"}
    forbidden = (
        ".activeDocument(",
        ".activeWindow(",
        ".activeView(",
        ".selectedNodes(",
        ".activeNode(",
        ".rootNode(",
        ".refreshProjection(",
        ".setAnnotation(",
        ".annotation(",
        ".removeAnnotation(",
        ".createGroupLayer(",
        ".projectionPixelData(",
    )

    for path in PACKAGE_ROOT.rglob("*.py"):
        relative = path.relative_to(PACKAGE_ROOT).as_posix()
        if relative.startswith("tests/") or path.name in allowed:
            continue
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{relative} contains native Krita API call {marker!r}"

