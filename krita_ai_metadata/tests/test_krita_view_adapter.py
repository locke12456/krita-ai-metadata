from __future__ import annotations

from krita_ai_metadata import krita_view_adapter
from krita_ai_metadata.krita_view_adapter import KritaViewAdapter


class FakeView:
    def __init__(self, nodes):
        self._nodes = nodes

    def selectedNodes(self):
        return self._nodes


class FakeWindow:
    def __init__(self, view):
        self._view = view

    def activeView(self):
        return self._view


class FakeApp:
    def __init__(self, window):
        self._window = window

    def activeWindow(self):
        return self._window


class FakeKrita:
    _app = None

    @staticmethod
    def instance():
        return FakeKrita._app


def test_selected_nodes_reads_active_view(monkeypatch):
    nodes = [object(), object()]
    FakeKrita._app = FakeApp(FakeWindow(FakeView(nodes)))
    monkeypatch.setattr(krita_view_adapter.krita, "Krita", FakeKrita)

    assert KritaViewAdapter().selected_nodes() == nodes


def test_selected_nodes_returns_empty_without_view(monkeypatch):
    FakeKrita._app = FakeApp(FakeWindow(None))
    monkeypatch.setattr(krita_view_adapter.krita, "Krita", FakeKrita)

    assert KritaViewAdapter().selected_nodes() == []
