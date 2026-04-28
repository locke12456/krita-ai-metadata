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