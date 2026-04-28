from __future__ import annotations

try:
    from PyQt6 import QtCore, QtGui, QtWidgets

    QT_BINDING = "PyQt6"
    IS_QT6 = True
except Exception as pyqt6_error:
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets

        QT_BINDING = "PyQt5"
        IS_QT6 = False
    except Exception as pyqt5_error:
        raise ImportError(
            "Unable to import Krita Qt bindings. Tried PyQt6 first, then PyQt5. "
            f"PyQt6 error: {pyqt6_error}; PyQt5 error: {pyqt5_error}"
        ) from pyqt5_error


QByteArray = QtCore.QByteArray
QBuffer = QtCore.QBuffer
QFile = QtCore.QFile
QIODevice = QtCore.QIODevice
QRect = QtCore.QRect
QSize = QtCore.QSize
Qt = QtCore.Qt

QAction = getattr(QtGui, "QAction", None)
if QAction is None:
    QAction = QtWidgets.QAction

QImage = QtGui.QImage
QImageReader = QtGui.QImageReader
QImageWriter = QtGui.QImageWriter
QPainter = QtGui.QPainter
QPixmap = QtGui.QPixmap

QCheckBox = QtWidgets.QCheckBox
QComboBox = QtWidgets.QComboBox
QFileDialog = QtWidgets.QFileDialog
QHBoxLayout = QtWidgets.QHBoxLayout
QInputDialog = QtWidgets.QInputDialog
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QMessageBox = QtWidgets.QMessageBox
QPushButton = QtWidgets.QPushButton
QScrollArea = QtWidgets.QScrollArea
QVBoxLayout = QtWidgets.QVBoxLayout
QWidget = QtWidgets.QWidget


def checked_state():
    return Qt.CheckState.Checked if IS_QT6 else Qt.Checked


def unchecked_state():
    return Qt.CheckState.Unchecked if IS_QT6 else Qt.Unchecked
def image_format_argb32():
    """Return the Qt5/Qt6 compatible QImage ARGB32 format enum."""
    image_format = getattr(QImage, "Format", None)
    if image_format is not None and hasattr(image_format, "Format_ARGB32"):
        return image_format.Format_ARGB32
    return QImage.Format_ARGB32


def write_only_mode():
    """Return the Qt5/Qt6 compatible QIODevice write-only open mode enum."""
    open_mode_flag = getattr(QIODevice, "OpenModeFlag", None)
    if open_mode_flag is not None and hasattr(open_mode_flag, "WriteOnly"):
        return open_mode_flag.WriteOnly
    return QIODevice.WriteOnly
