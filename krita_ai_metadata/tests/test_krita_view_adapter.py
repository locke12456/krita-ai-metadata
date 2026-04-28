from __future__ import annotations

from krita_ai_metadata import krita_view_adapter
from krita_ai_metadata.krita_view_adapter import KritaViewAdapter


def test_selected_nodes_reads_core_adapter_selection(monkeypatch):
    nodes = [object(), object()]
    monkeypatch.setattr(krita_view_adapter, "selected_krita_nodes", lambda: nodes)

    assert KritaViewAdapter().selected_nodes() == nodes


def test_selected_nodes_returns_empty_without_core_selection(monkeypatch):
    monkeypatch.setattr(krita_view_adapter, "selected_krita_nodes", lambda: [])

    assert KritaViewAdapter().selected_nodes() == []


def test_has_selection_uses_core_adapter_selection(monkeypatch):
    monkeypatch.setattr(krita_view_adapter, "selected_krita_nodes", lambda: [object()])

    assert KritaViewAdapter().has_selection() is True


def test_has_selection_is_false_without_core_selection(monkeypatch):
    monkeypatch.setattr(krita_view_adapter, "selected_krita_nodes", lambda: [])

    assert KritaViewAdapter().has_selection() is False
