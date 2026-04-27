from __future__ import annotations

import krita
from krita import DockWidget
from PyQt5.QtWidgets import QWidget

from .ui.docker_window import DockerWindow


class KritaAIMetadataExportDocker(DockWidget):
    """Main docker entry point for Krita AI Metadata Export."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Metadata Export")
        self._window = DockerWindow(self)
        self.setWidget(self._window)

    def canvasChanged(self, canvas: krita.Canvas):
        """Refresh docker state when Krita changes the active canvas."""
        self._window.refresh_from_canvas(canvas)

    def update_content(self):
        """Refresh docker content from the current active document."""
        self._window.refresh()