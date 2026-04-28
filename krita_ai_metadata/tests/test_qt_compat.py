from __future__ import annotations

import importlib
import sys
import types

import pytest


def _make_qt_modules(binding: str):
    qtcore = types.ModuleType(f"{binding}.QtCore")
    qtgui = types.ModuleType(f"{binding}.QtGui")
    qtwidgets = types.ModuleType(f"{binding}.QtWidgets")

    class FakeCheckState:
        Checked = object()
        Unchecked = object()

    class FakeQt6Qt:
        CheckState = FakeCheckState

    class FakeQt5Qt:
        Checked = object()
        Unchecked = object()

    class FakeQIODevice:
        WriteOnly = object()

    class FakeOpenModeFlag:
        WriteOnly = object()

    if binding == "PyQt6":
        FakeQIODevice.OpenModeFlag = FakeOpenModeFlag
        qtcore.Qt = FakeQt6Qt
    else:
        qtcore.Qt = FakeQt5Qt

    class FakeQImage:
        Format_ARGB32 = object()

    class FakeImageFormat:
        Format_ARGB32 = object()

    if binding == "PyQt6":
        FakeQImage.Format = FakeImageFormat

    qtcore.QByteArray = type("QByteArray", (), {})
    qtcore.QBuffer = type("QBuffer", (), {})
    qtcore.QFile = type("QFile", (), {})
    qtcore.QIODevice = FakeQIODevice
    qtcore.QRect = type("QRect", (), {})
    qtcore.QSize = type("QSize", (), {})

    qtgui.QAction = type("QAction", (), {})
    qtgui.QImage = FakeQImage
    qtgui.QImageReader = type("QImageReader", (), {})
    qtgui.QImageWriter = type("QImageWriter", (), {})
    qtgui.QPainter = type("QPainter", (), {})
    qtgui.QPixmap = type("QPixmap", (), {})

    for name in (
        "QAction",
        "QCheckBox",
        "QComboBox",
        "QFileDialog",
        "QHBoxLayout",
        "QInputDialog",
        "QLabel",
        "QLineEdit",
        "QMessageBox",
        "QPushButton",
        "QScrollArea",
        "QVBoxLayout",
        "QWidget",
    ):
        setattr(qtwidgets, name, type(name, (), {}))

    package = types.ModuleType(binding)
    package.__path__ = []
    package.QtCore = qtcore
    package.QtGui = qtgui
    package.QtWidgets = qtwidgets
    return package, qtcore, qtgui, qtwidgets


def _install_binding(monkeypatch, binding: str):
    package, qtcore, qtgui, qtwidgets = _make_qt_modules(binding)
    monkeypatch.setitem(sys.modules, binding, package)
    monkeypatch.setitem(sys.modules, f"{binding}.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, f"{binding}.QtGui", qtgui)
    monkeypatch.setitem(sys.modules, f"{binding}.QtWidgets", qtwidgets)
    return qtcore, qtgui, qtwidgets


def _block_binding(monkeypatch, binding: str) -> None:
    package = types.ModuleType(binding)
    package.__path__ = []
    monkeypatch.setitem(sys.modules, binding, package)
    monkeypatch.delitem(sys.modules, f"{binding}.QtCore", raising=False)
    monkeypatch.delitem(sys.modules, f"{binding}.QtGui", raising=False)
    monkeypatch.delitem(sys.modules, f"{binding}.QtWidgets", raising=False)


def _import_qt_compat_fresh(monkeypatch):
    monkeypatch.delitem(sys.modules, "krita_ai_metadata.qt_compat", raising=False)
    import krita_ai_metadata

    if hasattr(krita_ai_metadata, "qt_compat"):
        delattr(krita_ai_metadata, "qt_compat")

    return importlib.import_module("krita_ai_metadata.qt_compat")


def test_qt_compat_selects_pyqt6_when_available(monkeypatch) -> None:
    pyqt6_core, _, _ = _install_binding(monkeypatch, "PyQt6")
    _install_binding(monkeypatch, "PyQt5")

    qt_compat = _import_qt_compat_fresh(monkeypatch)

    assert qt_compat.QT_BINDING == "PyQt6"
    assert qt_compat.IS_QT6 is True
    assert qt_compat.QByteArray is pyqt6_core.QByteArray
    assert qt_compat.checked_state() is pyqt6_core.Qt.CheckState.Checked


def test_qt_compat_falls_back_to_pyqt5(monkeypatch) -> None:
    _block_binding(monkeypatch, "PyQt6")
    pyqt5_core, _, _ = _install_binding(monkeypatch, "PyQt5")

    qt_compat = _import_qt_compat_fresh(monkeypatch)

    assert qt_compat.QT_BINDING == "PyQt5"
    assert qt_compat.IS_QT6 is False
    assert qt_compat.QByteArray is pyqt5_core.QByteArray
    assert qt_compat.unchecked_state() is pyqt5_core.Qt.Unchecked


def test_qt_compat_raises_when_no_binding_is_available(monkeypatch) -> None:
    _block_binding(monkeypatch, "PyQt6")
    _block_binding(monkeypatch, "PyQt5")

    with pytest.raises(ImportError, match="Unable to import Krita Qt bindings"):
        _import_qt_compat_fresh(monkeypatch)
