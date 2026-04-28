from __future__ import annotations

from krita_ai_metadata import qt_compat


def test_qt_compat_exports_binding_name_and_core_classes() -> None:
    assert qt_compat.QT_BINDING in {"PyQt5", "PyQt6"}
    assert qt_compat.QByteArray is not None
    assert qt_compat.QMessageBox is not None


def test_qt_compat_enum_helpers_are_available() -> None:
    assert qt_compat.checked_state() is not None
    assert qt_compat.unchecked_state() is not None

from pathlib import Path


def test_qt_compat_source_prefers_pyqt6_then_pyqt5() -> None:
    source = Path(qt_compat.__file__).read_text(encoding="utf-8")

    assert "from PyQt6 import QtCore, QtGui, QtWidgets" in source
    assert "from PyQt5 import QtCore, QtGui, QtWidgets" in source
    assert source.index("from PyQt6 import QtCore, QtGui, QtWidgets") < source.index("from PyQt5 import QtCore, QtGui, QtWidgets")


def test_qt_compat_source_has_no_binding_import_error() -> None:
    source = Path(qt_compat.__file__).read_text(encoding="utf-8")

    assert "Unable to import Krita Qt bindings" in source

