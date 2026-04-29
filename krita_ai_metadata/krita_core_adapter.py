from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from krita import Krita

from .qt_compat import QByteArray, QImage, image_format_argb32, write_only_mode


@dataclass(frozen=True, slots=True)
class KritaBounds:
    x: int
    y: int
    width: int
    height: int

    @property
    def is_zero(self) -> bool:
        return self.width * self.height == 0

    @property
    def extent(self) -> tuple[int, int]:
        return self.width, self.height


@dataclass(slots=True)
class KritaDocumentRef:
    document: Any

    @property
    def filename(self) -> str:
        return self.document.fileName()

    @property
    def width(self) -> int:
        return int(self.document.width())

    @property
    def height(self) -> int:
        return int(self.document.height())

    @property
    def extent(self) -> tuple[int, int]:
        return self.width, self.height

    def check_color_mode(self) -> tuple[bool, str | None]:
        model = self.document.colorModel()
        if model != "RGBA":
            return False, f"Incompatible document: Color model must be RGB/Alpha (current model: {model})"
        depth = self.document.colorDepth()
        if depth != "U8":
            return False, f"Incompatible document: Color depth must be 8-bit integer (current depth: {depth})"
        return True, None

    def active_node(self) -> Any:
        return self.document.activeNode()

    def root_node(self) -> Any:
        return self.document.rootNode()

    def create_group_layer(self, name: str) -> Any:
        return self.document.createGroupLayer(name)

    def refresh_projection(self) -> None:
        self.document.refreshProjection()

    def find_annotation(self, key: str) -> QByteArray | None:
        result = self.document.annotation(f"ai_diffusion/{key}")
        if result is None:
            return None
        try:
            return result if result.size() > 0 else None
        except Exception:
            return result

    def annotate(self, key: str, value: QByteArray) -> None:
        self.document.setAnnotation(
            f"ai_diffusion/{key}",
            f"AI Diffusion Plugin: {key}",
            value,
        )

    def remove_annotation(self, key: str) -> None:
        self.document.removeAnnotation(f"ai_diffusion/{key}")


@dataclass(slots=True)
class KritaNodeRef:
    node: Any
    document_ref: KritaDocumentRef | None = None

    @property
    def id_string(self) -> str:
        return self.node.uniqueId().toString()

    @property
    def name(self) -> str:
        return self.node.name()

    @name.setter
    def name(self, value: str) -> None:
        self.node.setName(value)

    @property
    def type(self) -> str:
        return self.node.type()

    @property
    def visible(self) -> bool:
        return bool(self.node.visible())

    @property
    def is_visible(self) -> bool:
        return self.visible

    @property
    def is_root(self) -> bool:
        return self.node.parentNode() is None

    @property
    def parent_layer(self) -> KritaNodeRef | None:
        parent = self.node.parentNode()
        if parent is None:
            return None
        return KritaNodeRef(parent, self.document_ref)

    @property
    def child_layers(self) -> list[KritaNodeRef]:
        return [
            KritaNodeRef(child, self.document_ref)
            for child in list(self.node.childNodes() or [])
            if child.type()
        ]

    @property
    def bounds(self) -> KritaBounds:
        rect = self.node.bounds()
        return KritaBounds(rect.x(), rect.y(), rect.width(), rect.height())

    def refresh(self) -> None:
        try:
            self.node.setBlendingMode(self.node.blendingMode())
        except Exception:
            if self.document_ref is not None:
                self.document_ref.refresh_projection()

    def get_pixels(self, bounds: KritaBounds | None = None) -> "KritaRenderedImage":
        return render_node_projection(self, bounds)


class KritaRenderedImage:
    def __init__(self, data: QByteArray, bounds: KritaBounds):
        self._data = data
        self.bounds = bounds

    @property
    def width(self) -> int:
        return self.bounds.width

    @property
    def height(self) -> int:
        return self.bounds.height

    @property
    def extent(self) -> tuple[int, int]:
        return self.width, self.height

    def _to_qimage(self) -> QImage:
        stride = self.width * 4
        image = QImage(self._data, self.width, self.height, stride, image_format_argb32())
        return QImage(image)

    def to_bytes(self) -> QByteArray:
        from .qt_compat import QBuffer

        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(write_only_mode())
        image = self._to_qimage()
        image.save(buffer, "PNG")
        buffer.close()
        return data

    @staticmethod
    def save_png_w_itxt(img_path: str | Path, png_data: bytes, keyword: str, text: str) -> None:
        if png_data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Not a valid PNG file")

        offset = 8
        ihdr_inserted = False

        with open(img_path, "wb") as handle:
            handle.write(png_data[:8])

            while offset < len(png_data):
                length = struct.unpack(">I", png_data[offset : offset + 4])[0]
                chunk_type = png_data[offset + 4 : offset + 8]
                chunk_data = png_data[offset + 8 : offset + 8 + length]
                crc = png_data[offset + 8 + length : offset + 12 + length]
                offset += 12 + length

                handle.write(struct.pack(">I", length))
                handle.write(chunk_type)
                handle.write(chunk_data)
                handle.write(crc)

                if not ihdr_inserted and chunk_type == b"IHDR":
                    keyword_bytes = keyword.encode("latin1")
                    text_bytes = text.encode("utf-8")
                    itxt_data = (
                        keyword_bytes
                        + b"\x00"
                        + b"\x00"
                        + b"\x00"
                        + b"\x00"
                        + b"\x00"
                        + text_bytes
                    )
                    handle.write(struct.pack(">I", len(itxt_data)))
                    handle.write(b"iTXt")
                    handle.write(itxt_data)
                    handle.write(struct.pack(">I", zlib.crc32(b"iTXt" + itxt_data) & 0xFFFFFFFF))
                    ihdr_inserted = True

    def save(self, filepath: str | Path) -> None:
        Path(filepath).write_bytes(bytes(self.to_bytes()))

    def save_png_with_metadata(self, filepath: str | Path, metadata_text: str, format: Any = None) -> None:
        self.save_png_w_itxt(filepath, bytes(self.to_bytes()), "parameters", metadata_text)


def active_krita_document() -> KritaDocumentRef | None:
    document = Krita.instance().activeDocument()
    if document is None:
        return None
    return KritaDocumentRef(document)


def all_krita_nodes(document_ref: KritaDocumentRef | None = None) -> list[KritaNodeRef]:
    """Return all native Krita nodes below the document root for manual-only mode."""
    document_ref = document_ref or active_krita_document()
    if document_ref is None:
        return []

    try:
        root = document_ref.root_node()
    except Exception:
        return []

    result: list[KritaNodeRef] = []

    def visit(node: Any) -> None:
        if node is None:
            return
        node_ref = KritaNodeRef(node, document_ref)
        result.append(node_ref)
        try:
            children = list(node.childNodes() or [])
        except Exception:
            children = []
        for child in children:
            visit(child)

    visit(root)
    return result


def selected_krita_nodes() -> list[KritaNodeRef]:
    app = Krita.instance()
    window = app.activeWindow()
    if window is None:
        return []
    view = window.activeView()
    if view is None:
        return []
    document_ref = active_krita_document()
    return [KritaNodeRef(node, document_ref) for node in list(view.selectedNodes() or [])]


def wrap_node(node: Any) -> KritaNodeRef:
    return KritaNodeRef(node, active_krita_document())


def add_layer_only_paint_layer(
    document_ref: KritaDocumentRef,
    name: str,
    png_bytes: bytes | None = None,
    parent_node: Any | None = None,
    above_node: Any | None = None,
) -> KritaNodeRef:
    """Add a paint layer without creating a group."""
    if document_ref is None:
        raise ValueError("document_ref is required")
    if not name:
        raise ValueError("Layer name is required")

    document = document_ref.document
    create_node = getattr(document, "createNode", None)
    if not callable(create_node):
        raise RuntimeError("Krita document does not expose createNode")

    node = create_node(name, "paintLayer")

    if png_bytes:
        set_pixel_data = getattr(node, "setPixelData", None)
        if callable(set_pixel_data):
            image = QImage()
            if not image.loadFromData(png_bytes, "PNG"):
                raise ValueError("Candidate layer PNG bytes could not be decoded")
            image = image.convertToFormat(image_format_argb32())
            width = int(image.width())
            height = int(image.height())
            ptr = image.bits()
            try:
                ptr.setsize(image.sizeInBytes())
            except Exception:
                ptr.setsize(image.byteCount())
            set_pixel_data(QByteArray(bytes(ptr)), 0, 0, width, height)

    parent = parent_node or getattr(document, "rootNode", lambda: None)()
    if parent is None:
        raise RuntimeError("Unable to resolve target parent node")
    add_child = getattr(parent, "addChildNode", None)
    if not callable(add_child):
        raise RuntimeError("Target parent node does not expose addChildNode")

    add_child(node, above_node)
    document_ref.refresh_projection()
    return KritaNodeRef(node, document_ref)


def create_group_for_nodes(
    document_ref: KritaDocumentRef,
    node_refs: list[KritaNodeRef],
    group_name: str,
) -> KritaNodeRef:
    live_nodes = [node_ref for node_ref in node_refs if node_ref.node is not None]
    if not live_nodes:
        raise ValueError("Cannot create a metadata group without live layers")

    anchor = live_nodes[0].node
    parent = anchor.parentNode()
    if parent is None:
        raise ValueError("Cannot create a metadata group for a root or detached layer")

    group_node = document_ref.create_group_layer(group_name)

    # Krita native createGroupLayer() may return a detached node. Attach the
    # group to the source parent before removing any selected layer; otherwise
    # moving layers into the detached group can make them disappear from the
    # document tree, especially when rebuilding Krita 5 records in Krita 6.
    parent.addChildNode(group_node, anchor)
    group_ref = KritaNodeRef(group_node, document_ref)

    move_nodes_to_group(document_ref, live_nodes, group_ref)
    return group_ref


def move_nodes_to_group(
    document_ref: KritaDocumentRef,
    node_refs: list[KritaNodeRef],
    group_ref: KritaNodeRef,
) -> None:
    if group_ref.node.parentNode() is None:
        raise ValueError("Cannot move layers into a detached metadata group")

    for node_ref in node_refs:
        if node_ref.node == group_ref.node:
            continue
        parent = node_ref.node.parentNode()
        if parent is None:
            continue
        parent.removeChildNode(node_ref.node)
        group_ref.node.addChildNode(node_ref.node, None)
    document_ref.refresh_projection()


def _native_node(layer_ref: Any) -> Any:
    """Return the native Krita node for a wrapper or native node input."""
    return getattr(layer_ref, "node", layer_ref)


def _document_ref_for_layer(layer_ref: Any) -> KritaDocumentRef | None:
    """Resolve the document wrapper from a layer wrapper when possible."""
    document_ref = getattr(layer_ref, "document_ref", None)
    if document_ref is not None:
        return document_ref
    return active_krita_document()


def _child_nodes(parent_node: Any) -> list[Any]:
    """Return parent children in Krita's layer order.

    The existing krita-ai-diffusion LayerManager treats childNodes() as
    bottom-to-top order: the last child is top-most, and addChildNode(node, None)
    moves a layer to the top.
    """
    try:
        return list(parent_node.childNodes() or [])
    except Exception:
        return []


def _node_index(parent_node: Any, node: Any) -> int:
    """Return a node index under parent, or -1 when it cannot be found."""
    for index, child in enumerate(_child_nodes(parent_node)):
        if child == node:
            return index
    return -1


def _assert_same_parent(node: Any, target_node: Any) -> Any:
    """Return the shared parent or raise a precise merge/reorder error."""
    if node is None or target_node is None:
        raise RuntimeError("Layer and target nodes are required.")
    if node == target_node:
        raise RuntimeError("Cannot operate on the same source and target layer.")

    parent = node.parentNode()
    target_parent = target_node.parentNode()
    if parent is None or target_parent is None:
        raise RuntimeError("Cannot operate on detached or root layers.")
    if parent != target_parent:
        raise RuntimeError("Generated layer and target layer must share the same parent.")
    return parent


def find_krita_node_by_id(
    document_ref: KritaDocumentRef | None,
    layer_id: str,
) -> KritaNodeRef | None:
    """Find a layer wrapper by stable Krita node id."""
    target_id = str(layer_id or "")
    if not target_id:
        return None
    for node_ref in all_krita_nodes(document_ref):
        if node_ref.id_string == target_id:
            return node_ref
    return None


def set_layer_visible(layer_ref: Any, visible: bool) -> None:
    """Set layer visibility through a runtime-checked Krita node setter."""
    node = _native_node(layer_ref)
    set_visible = getattr(node, "setVisible", None)
    if not callable(set_visible):
        raise RuntimeError("Krita node does not expose setVisible().")
    set_visible(bool(visible))
    document_ref = _document_ref_for_layer(layer_ref)
    if document_ref is not None:
        document_ref.refresh_projection()


def move_layer_immediately_above(
    document_ref: KritaDocumentRef | None,
    layer_ref: Any,
    target_ref: Any,
) -> KritaNodeRef:
    """Move layer_ref to the immediate-above position for target_ref.

    Krita mergeDown() always merges the current layer into its immediate lower
    sibling. Therefore reorder must not merely put the layer somewhere above the
    target; it must make the generated layer the direct sibling above the target
    and verify that order before merge is allowed.
    """
    node = _native_node(layer_ref)
    target_node = _native_node(target_ref)
    parent = _assert_same_parent(node, target_node)

    remove_child = getattr(parent, "removeChildNode", None)
    add_child = getattr(parent, "addChildNode", None)
    if not callable(remove_child) or not callable(add_child):
        raise RuntimeError("Layer parent does not expose removeChildNode/addChildNode.")

    current_node_index = _node_index(parent, node)
    current_target_index = _node_index(parent, target_node)
    if current_node_index < 0 or current_target_index < 0:
        raise RuntimeError("Generated layer or target layer is missing from its parent.")

    # childNodes() is bottom-to-top. Immediate-above means generated index is
    # exactly target index + 1. If already correct, do not disturb the tree.
    if current_node_index != current_target_index + 1:
        remove_child(node)
        add_child(node, target_node)

    resolved_document = document_ref or _document_ref_for_layer(layer_ref)
    if resolved_document is not None:
        resolved_document.refresh_projection()

    parent = target_node.parentNode()
    node_index = _node_index(parent, node)
    target_index = _node_index(parent, target_node)
    if node_index != target_index + 1:
        raise RuntimeError(
            "Generated layer could not be moved directly above the target layer; "
            "refusing mergeDown() to avoid merging into the wrong layer."
        )

    return KritaNodeRef(node, resolved_document)


def move_layer_above(
    document_ref: KritaDocumentRef | None,
    layer_ref: Any,
    anchor_ref: Any,
) -> KritaNodeRef:
    """Backward-compatible alias for direct-above reorder."""
    return move_layer_immediately_above(document_ref, layer_ref, anchor_ref)


def merge_layer_down(layer_ref: Any) -> KritaNodeRef | None:
    """Merge a layer down through a runtime-checked Krita node merge API."""
    node = _native_node(layer_ref)
    merge_down = getattr(node, "mergeDown", None)
    if not callable(merge_down):
        raise RuntimeError("Krita node does not expose mergeDown().")

    result = merge_down()
    document_ref = _document_ref_for_layer(layer_ref)
    if document_ref is not None:
        document_ref.refresh_projection()

    if result is None:
        return None
    return KritaNodeRef(result, document_ref)


def merge_layer_into_target(
    document_ref: KritaDocumentRef | None,
    layer_ref: Any,
    target_ref: Any,
) -> KritaNodeRef:
    """Safely merge layer_ref into target_ref and return the live merged layer.

    Krita mergeDown() may return None even after a successful merge. The Repair
    Docker needs the live merged layer id for later [X] delete, so this helper
    resolves the surviving/recreated node from the parent child list when the
    direct API return value is missing.
    """
    moved = move_layer_immediately_above(document_ref, layer_ref, target_ref)

    moved_node = _native_node(moved)
    target_node = _native_node(target_ref)
    parent = _assert_same_parent(moved_node, target_node)

    def node_id(node: Any) -> str:
        unique_id = getattr(node, "uniqueId", None)
        if callable(unique_id):
            try:
                return str(unique_id().toString())
            except Exception:
                return ""
        return ""

    target_id = node_id(target_node)
    generated_id = node_id(moved_node)
    before_nodes = _child_nodes(parent)
    before_ids = {node_id(node) for node in before_nodes if node_id(node)}
    target_index_before = _node_index(parent, target_node)

    result = merge_layer_down(moved)
    if result is not None:
        return result

    if document_ref is not None:
        document_ref.refresh_projection()

    after_nodes = _child_nodes(parent)

    # 1) Some Krita builds keep the target node alive and merge pixels into it.
    for node in after_nodes:
        if target_id and node_id(node) == target_id:
            return KritaNodeRef(node, document_ref)

    # 2) Some builds keep the generated node alive after mergeDown().
    for node in after_nodes:
        if generated_id and node_id(node) == generated_id:
            return KritaNodeRef(node, document_ref)

    # 3) Some builds replace both nodes with a new merged node.
    new_nodes = [
        node
        for node in after_nodes
        if node_id(node) and node_id(node) not in before_ids
    ]
    if len(new_nodes) == 1:
        return KritaNodeRef(new_nodes[0], document_ref)

    # 4) Last safe fallback: mergeDown should leave the merged node around the
    # original target position after generated+target collapsed into one layer.
    if 0 <= target_index_before < len(after_nodes):
        return KritaNodeRef(after_nodes[target_index_before], document_ref)

    raise RuntimeError("mergeDown() finished but the live merged layer could not be resolved.")


def delete_layer(layer_ref: Any) -> None:
    """Delete a Krita layer through a runtime-checked node API.

    Prefer Node.remove() when available because Krita owns the undo/document
    bookkeeping for that operation. Fall back to parent.removeChildNode(node)
    only when remove() is unavailable.
    """
    node = _native_node(layer_ref)
    if node is None:
        raise RuntimeError("Layer node is required for delete.")

    parent = node.parentNode()
    if parent is None:
        raise RuntimeError("Cannot delete a detached or root layer.")

    document_ref = _document_ref_for_layer(layer_ref)

    remove = getattr(node, "remove", None)
    if callable(remove):
        remove()
    else:
        remove_child = getattr(parent, "removeChildNode", None)
        if not callable(remove_child):
            raise RuntimeError("Krita node does not expose remove(), and parent does not expose removeChildNode().")
        remove_child(node)

    if document_ref is not None:
        document_ref.refresh_projection()


def refresh_projection(document_ref: KritaDocumentRef) -> None:
    document_ref.refresh_projection()


def render_node_projection(
    node_ref: KritaNodeRef,
    bounds: KritaBounds | None = None,
) -> KritaRenderedImage:
    bounds = bounds or node_ref.bounds
    if bounds.is_zero and node_ref.document_ref is not None:
        bounds = KritaBounds(0, 0, node_ref.document_ref.width, node_ref.document_ref.height)
    data = node_ref.node.projectionPixelData(bounds.x, bounds.y, bounds.width, bounds.height)
    return KritaRenderedImage(data, bounds)