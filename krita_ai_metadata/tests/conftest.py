from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


TESTS_DIR = Path(__file__).resolve().parent
PKG_DIR = TESTS_DIR.parent
REPO_ROOT = PKG_DIR.parent


def _add_path(path: Path) -> None:
    text = str(path)
    if path.exists() and text not in sys.path:
        sys.path.insert(0, text)


# Make the real package `krita_ai_metadata` importable.
_add_path(REPO_ROOT)


# Local pytest runs do not provide Krita's embedded `krita` module.
# Some environments provide a partial `krita` placeholder, so always patch
# missing attributes instead of only creating a module when it is absent.
krita_stub = sys.modules.get("krita")
if krita_stub is None:
    krita_stub = types.ModuleType("krita")
    sys.modules["krita"] = krita_stub


class _Signal:
    def connect(self, *_args, **_kwargs):
        return None


class _Action:
    def __init__(self):
        self.triggered = _Signal()


class _KritaApp:
    def addExtension(self, *_args, **_kwargs):
        return None

    def addDockWidgetFactory(self, *_args, **_kwargs):
        return None

    def activeWindow(self):
        return None

    def notifier(self):
        return types.SimpleNamespace(
            setActive=lambda *_args, **_kwargs: None,
            applicationClosing=_Signal(),
        )

    def version(self):
        return "pytest-stub"


class Krita:
    _app = _KritaApp()

    @staticmethod
    def instance():
        return Krita._app


class Extension:
    def __init__(self, parent=None):
        self.parent = parent

    def setup(self):
        return None

    def createActions(self, window):
        return None


class DockWidget:
    def __init__(self):
        self._widget = None
        self._window_title = ""

    def setWindowTitle(self, title):
        self._window_title = title

    def setWidget(self, widget):
        self._widget = widget


class DockWidgetFactory:
    def __init__(self, identifier, dock_area, widget_class):
        self.identifier = identifier
        self.dock_area = dock_area
        self.widget_class = widget_class


class DockWidgetFactoryBase:
    DockRight = "DockRight"


class Canvas:
    pass


for name, value in {
    "Krita": Krita,
    "Extension": Extension,
    "DockWidget": DockWidget,
    "DockWidgetFactory": DockWidgetFactory,
    "DockWidgetFactoryBase": DockWidgetFactoryBase,
    "Canvas": Canvas,
}.items():
    if not hasattr(krita_stub, name):
        setattr(krita_stub, name, value)


# Do NOT import the real ai_diffusion package during local unit tests.
# Source-only krita-ai-diffusion executes release dependency checks in
# ai_diffusion/__init__.py and fails outside of the plugin bundle.
if "ai_diffusion" not in sys.modules:
    ai_diffusion_pkg = types.ModuleType("ai_diffusion")
    ai_diffusion_pkg.__path__ = []
    sys.modules["ai_diffusion"] = ai_diffusion_pkg


# ---- ai_diffusion.image -------------------------------------------------
image_mod = types.ModuleType("ai_diffusion.image")


@dataclass(frozen=True)
class Bounds:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    @property
    def is_zero(self) -> bool:
        return self.width == 0 or self.height == 0


class Image:
    @staticmethod
    def save_png_with_metadata(filepath: str, metadata_text: str, format: Any = None) -> None:
        Path(filepath).write_bytes(b"")


image_mod.Bounds = Bounds
image_mod.Image = Image
sys.modules["ai_diffusion.image"] = image_mod


# ---- ai_diffusion.jobs --------------------------------------------------
jobs_mod = types.ModuleType("ai_diffusion.jobs")


@dataclass
class JobRegion:
    layer_id: str = ""
    prompt: str = ""
    bounds: Bounds = field(default_factory=Bounds)
    is_background: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobRegion":
        bounds = data.get("bounds", Bounds())
        if isinstance(bounds, (list, tuple)):
            bounds = Bounds(*bounds)
        elif isinstance(bounds, dict):
            bounds = Bounds(**bounds)
        return cls(
            layer_id=data.get("layer_id", ""),
            prompt=data.get("prompt", ""),
            bounds=bounds,
            is_background=bool(data.get("is_background", False)),
        )


@dataclass
class JobParams:
    bounds: Bounds = field(default_factory=Bounds)
    name: str = ""
    regions: list[JobRegion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    has_mask: bool = False
    is_layered: bool = False
    frame: tuple[int, int, int] = (0, 0, 0)
    animation_id: str = ""
    resize_canvas: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobParams":
        bounds = data.get("bounds", Bounds())
        if isinstance(bounds, (list, tuple)):
            bounds = Bounds(*bounds)
        elif isinstance(bounds, dict):
            bounds = Bounds(**bounds)

        regions = [
            item if isinstance(item, JobRegion) else JobRegion.from_dict(item)
            for item in data.get("regions", [])
        ]

        frame = data.get("frame", (0, 0, 0))
        if isinstance(frame, list):
            frame = tuple(frame)

        return cls(
            bounds=bounds,
            name=data.get("name", ""),
            regions=regions,
            metadata=dict(data.get("metadata", {})),
            seed=int(data.get("seed", 0) or 0),
            has_mask=bool(data.get("has_mask", False)),
            is_layered=bool(data.get("is_layered", False)),
            frame=frame,
            animation_id=data.get("animation_id", ""),
            resize_canvas=bool(data.get("resize_canvas", False)),
        )


jobs_mod.JobRegion = JobRegion
jobs_mod.JobParams = JobParams
sys.modules["ai_diffusion.jobs"] = jobs_mod


# ---- ai_diffusion.layer -------------------------------------------------
layer_mod = types.ModuleType("ai_diffusion.layer")


class LayerType(Enum):
    group = "grouplayer"
    paint = "paintlayer"

    @property
    def is_image(self) -> bool:
        return True


class Layer:
    pass


class LayerManager:
    pass


layer_mod.LayerType = LayerType
layer_mod.Layer = Layer
layer_mod.LayerManager = LayerManager
sys.modules["ai_diffusion.layer"] = layer_mod


# ---- ai_diffusion.document ----------------------------------------------
document_mod = types.ModuleType("ai_diffusion.document")


class Document:
    pass


document_mod.Document = Document
sys.modules["ai_diffusion.document"] = document_mod


# ---- ai_diffusion.text --------------------------------------------------
text_mod = types.ModuleType("ai_diffusion.text")


def create_img_metadata(params: JobParams) -> str:
    prompt = params.metadata.get("prompt") or params.name
    negative = params.metadata.get("negative_prompt", "")
    sampler = params.metadata.get("sampler", "")
    steps = params.metadata.get("steps", "")
    guidance = params.metadata.get("guidance", "")
    checkpoint = params.metadata.get("checkpoint", "")

    lines = [str(prompt)]
    if negative:
        lines.append(f"Negative prompt: {negative}")

    fields = []
    if steps != "":
        fields.append(f"Steps: {steps}")
    if sampler:
        fields.append(f"Sampler: {sampler}")
    if guidance != "":
        fields.append(f"CFG scale: {guidance}")
    if params.seed:
        fields.append(f"Seed: {params.seed}")
    if checkpoint:
        fields.append(f"Model: {checkpoint}")

    if fields:
        lines.append(", ".join(fields))

    return "\n".join(lines)


text_mod.create_img_metadata = create_img_metadata
sys.modules["ai_diffusion.text"] = text_mod

# ---- additional docker/test stubs -----------------------------------------
# These stubs keep local pytest collection working outside Krita while avoiding
# the real ai_diffusion package import side effects.

# ---- PyQt5.QtCore / PyQt5.QtWidgets ---------------------------------------
pyqt5_pkg = sys.modules.get("PyQt5")
if pyqt5_pkg is None:
    pyqt5_pkg = types.ModuleType("PyQt5")
    pyqt5_pkg.__path__ = []
    sys.modules["PyQt5"] = pyqt5_pkg

qtcore_mod = sys.modules.get("PyQt5.QtCore")
if qtcore_mod is None:
    qtcore_mod = types.ModuleType("PyQt5.QtCore")
    sys.modules["PyQt5.QtCore"] = qtcore_mod


class QByteArray(bytes):
    def __new__(cls, value=b""):
        return bytes.__new__(cls, value)


if not hasattr(qtcore_mod, "QByteArray"):
    qtcore_mod.QByteArray = QByteArray

qtwidgets_mod = sys.modules.get("PyQt5.QtWidgets")
if qtwidgets_mod is None:
    qtwidgets_mod = types.ModuleType("PyQt5.QtWidgets")
    sys.modules["PyQt5.QtWidgets"] = qtwidgets_mod


class _Widget:
    def __init__(self, *args, **kwargs):
        self._text = ""
        self._visible = True
        self._checked = False
        self.clicked = _Signal()
        self.triggered = _Signal()
        self.stateChanged = _Signal()

    def setText(self, value):
        self._text = str(value)

    def text(self):
        return self._text

    def setWordWrap(self, *_args, **_kwargs):
        return None

    def setStyleSheet(self, *_args, **_kwargs):
        return None

    def setVisible(self, value):
        self._visible = bool(value)

    def setChecked(self, value):
        self._checked = bool(value)

    def isChecked(self):
        return self._checked

    def setLayout(self, layout):
        self._layout = layout

    def deleteLater(self):
        return None


class QWidget(_Widget):
    pass


class QLabel(_Widget):
    pass


class QPushButton(_Widget):
    pass


class QCheckBox(_Widget):
    pass


class QLineEdit(_Widget):
    def __init__(self, text="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text = str(text)


class _LayoutItem:
    def __init__(self, widget=None):
        self._widget = widget

    def widget(self):
        return self._widget


class _Layout:
    def __init__(self, *args, **kwargs):
        self._items = []

    def addWidget(self, widget):
        self._items.append(_LayoutItem(widget))

    def addLayout(self, layout):
        self._items.append(_LayoutItem(None))

    def addStretch(self, *args, **kwargs):
        self._items.append(_LayoutItem(None))

    def count(self):
        return len(self._items)

    def takeAt(self, index):
        return self._items.pop(index)


class QVBoxLayout(_Layout):
    pass


class QHBoxLayout(_Layout):
    pass


class QFileDialog:
    @staticmethod
    def getExistingDirectory(*_args, **_kwargs):
        return ""


class QInputDialog:
    @staticmethod
    def getText(*_args, **kwargs):
        return kwargs.get("text", ""), False


class QMessageBox:
    @staticmethod
    def warning(*_args, **_kwargs):
        return None

    @staticmethod
    def information(*_args, **_kwargs):
        return None


for name, value in {
    "QWidget": QWidget,
    "QLabel": QLabel,
    "QPushButton": QPushButton,
    "QCheckBox": QCheckBox,
    "QLineEdit": QLineEdit,
    "QVBoxLayout": QVBoxLayout,
    "QHBoxLayout": QHBoxLayout,
    "QFileDialog": QFileDialog,
    "QInputDialog": QInputDialog,
    "QMessageBox": QMessageBox,
}.items():
    if not hasattr(qtwidgets_mod, name):
        setattr(qtwidgets_mod, name, value)


# ---- ai_diffusion.root ---------------------------------------------------
root_mod = types.ModuleType("ai_diffusion.root")


class _Root:
    def model_for_active_document(self):
        return None

    @property
    def active_model(self):
        return None


root_mod.root = _Root()
sys.modules["ai_diffusion.root"] = root_mod


# ---- ai_diffusion.jobs additions ----------------------------------------
class JobState(Enum):
    finished = "finished"
    queued = "queued"
    executing = "executing"
    failed = "failed"


jobs_mod.JobState = JobState


# ---- ai_diffusion.layer additions ---------------------------------------
class RestoreActiveLayer:
    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


layer_mod.RestoreActiveLayer = RestoreActiveLayer


# ---- ai_diffusion.document additions ------------------------------------
class KritaDocument(Document):
    filename = ""
    layers = None

    @staticmethod
    def active():
        return None

    @staticmethod
    def active_instance():
        return None

    def check_color_mode(self):
        return True, ""

    @property
    def is_valid(self):
        return True


Document.KritaDocument = KritaDocument
document_mod.KritaDocument = KritaDocument


# ---- ai_diffusion.image additions ---------------------------------------
def _image_save(self, filepath, *args, **kwargs):
    Path(filepath).write_bytes(b"")


Image.save = _image_save

