from __future__ import annotations

from types import SimpleNamespace

from krita_ai_metadata import krita_core_adapter
from krita_ai_metadata.krita_core_adapter import (
    KritaDocumentRef,
    KritaNodeRef,
    create_group_for_nodes,
    render_node_projection,
    selected_krita_nodes,
)


class FakeId:
    def __init__(self, value: str):
        self.value = value

    def toString(self):
        return self.value


class FakeRect:
    def x(self):
        return 1

    def y(self):
        return 2

    def width(self):
        return 3

    def height(self):
        return 4


class FakeNode:
    def __init__(self, node_id="node-1", name="Node", node_type="paintlayer"):
        self._id = node_id
        self._name = name
        self._type = node_type
        self._parent = None
        self.children = []
        self.removed = []
        self.added = []

    def uniqueId(self):
        return FakeId(self._id)

    def name(self):
        return self._name

    def setName(self, value):
        self._name = value

    def type(self):
        return self._type

    def visible(self):
        return True

    def bounds(self):
        return FakeRect()

    def parentNode(self):
        return self._parent

    def childNodes(self):
        return self.children

    def removeChildNode(self, node):
        self.removed.append(node)
        node._parent = None

    def addChildNode(self, node, above):
        self.added.append((node, above))
        self.children.append(node)
        node._parent = self

    def projectionPixelData(self, x, y, width, height):
        return b"\x00" * (width * height * 4)


class FakeDocument:
    def __init__(self):
        self.annotations = {}
        self.refreshed = 0
        self.group = FakeNode("group-1", "Group", "grouplayer")
        self.active = FakeNode("active", "Active")

    def fileName(self):
        return "test.kra"

    def width(self):
        return 10

    def height(self):
        return 20

    def colorModel(self):
        return "RGBA"

    def colorDepth(self):
        return "U8"

    def activeNode(self):
        return self.active

    def rootNode(self):
        return FakeNode("root", "Root", "root")

    def createGroupLayer(self, name):
        self.group.setName(name)
        return self.group

    def refreshProjection(self):
        self.refreshed += 1

    def annotation(self, key):
        return self.annotations.get(key)

    def setAnnotation(self, key, description, value):
        self.annotations[key] = value

    def removeAnnotation(self, key):
        self.annotations.pop(key, None)


def test_document_ref_annotation_protocol() -> None:
    doc = FakeDocument()
    ref = KritaDocumentRef(doc)

    ref.annotate("sync.json", b"{}")

    assert ref.find_annotation("sync.json") == b"{}"
    ref.remove_annotation("sync.json")
    assert ref.find_annotation("sync.json") is None


def test_selected_krita_nodes_wraps_active_view_nodes(monkeypatch) -> None:
    node = FakeNode()
    document = FakeDocument()
    app = SimpleNamespace(
        activeDocument=lambda: document,
        activeWindow=lambda: SimpleNamespace(
            activeView=lambda: SimpleNamespace(selectedNodes=lambda: [node])
        ),
    )
    monkeypatch.setattr(krita_core_adapter.Krita, "instance", lambda: app)

    refs = selected_krita_nodes()

    assert len(refs) == 1
    assert refs[0].id_string == "node-1"


def test_create_group_for_nodes_moves_nodes_and_refreshes() -> None:
    document = FakeDocument()
    parent = FakeNode("parent", "Parent", "grouplayer")
    node = FakeNode("child", "Child")
    node._parent = parent
    ref = KritaDocumentRef(document)

    group = create_group_for_nodes(ref, [KritaNodeRef(node, ref)], "New Group")

    assert group.name == "New Group"
    assert parent.removed == [node]
    assert group.node.added[0][0] is node
    assert document.refreshed == 1


def test_render_node_projection_returns_rendered_image() -> None:
    document = FakeDocument()
    node_ref = KritaNodeRef(FakeNode(), KritaDocumentRef(document))

    image = render_node_projection(node_ref)

    assert image.width == 3
    assert image.height == 4
