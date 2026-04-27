from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from krita import Krita
from PyQt5.QtCore import QByteArray

from ai_diffusion.document import KritaDocument
from ai_diffusion.image import Bounds, Image
from ai_diffusion.layer import Layer, LayerManager, LayerType


DEFAULT_PARAMETERS = (
    "probe export\n"
    "Negative prompt: \n"
    "Steps: 20, Sampler: probe, CFG scale: 7.0, Seed: 0, Size: 1x1, Model hash: unknown, Model: probe"
)


def active_output_dir() -> Path:
    doc = Krita.instance().activeDocument()
    if doc and doc.fileName():
        base = Path(doc.fileName()).parent
    else:
        base = Path.home()
    output_dir = base / "krita_export_probe"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def active_document() -> KritaDocument:
    document = KritaDocument.active()
    if document is None:
        raise RuntimeError("No active Krita document")
    ok, message = document.check_color_mode()
    if not ok:
        raise RuntimeError(message or "Active document is not compatible")
    return document


def selected_nodes() -> list[Any]:
    window = Krita.instance().activeWindow()
    if window is None:
        return []
    view = window.activeView()
    if view is None:
        return []
    nodes = view.selectedNodes()
    return list(nodes or [])


def selected_layers(layer_manager: LayerManager) -> list[Layer]:
    layers: list[Layer] = []
    for node in selected_nodes():
        try:
            layers.append(layer_manager.wrap(node))
        except Exception:
            continue
    return layers


def first_export_layer(layer_manager: LayerManager) -> Layer:
    selected = selected_layers(layer_manager)
    if selected:
        return selected[0]
    active = layer_manager.active
    if active is not None:
        return active
    for layer in layer_manager.all:
        if layer.type is LayerType.group or layer.type.is_image:
            return layer
    raise RuntimeError("No exportable layer found")


def export_bounds(layer: Layer, fallback: Bounds) -> Bounds:
    bounds = layer.bounds
    if bounds.is_zero:
        return fallback
    return bounds


def read_parameters_from_png(path: Path) -> str | None:
    data = path.read_bytes()
    marker = b"parameters\x00\x00\x00\x00\x00"
    index = data.find(marker)
    if index < 0:
        return None
    start = index + len(marker)
    end = data.find(b"IEND", start)
    if end < 0:
        end = len(data)
    return data[start:end].decode("utf-8", errors="ignore").strip("\x00\r\n ")


def write_sidecar(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_probe(output_dir: str | Path | None = None, parameters: str = DEFAULT_PARAMETERS) -> dict[str, Any]:
    document = active_document()
    target = first_export_layer(document.layers)
    bounds = export_bounds(target, Bounds(0, 0, *document.extent))
    image: Image = target.get_pixels(bounds)

    output = Path(output_dir) if output_dir is not None else active_output_dir()
    output.mkdir(parents=True, exist_ok=True)

    key = "probe"
    png_path = output / f"{key}.png"
    json_path = output / f"{key}.json"

    image.save_png_with_metadata(png_path, parameters)
    embedded = read_parameters_from_png(png_path)

    payload = {
        "version": 1,
        "key": key,
        "target_name": target.name,
        "target_id": target.id_string,
        "target_type": target.type.value,
        "bounds": [bounds.x, bounds.y, bounds.width, bounds.height],
        "png_path": str(png_path),
        "a1111_parameters": parameters,
        "metadata_readback_ok": embedded is not None and parameters in embedded,
    }
    write_sidecar(json_path, payload)

    return {
        "png": str(png_path),
        "json": str(json_path),
        "metadata_readback_ok": payload["metadata_readback_ok"],
        "target": target.name,
    }


def run_from_krita() -> None:
    result = run_probe()
    Krita.instance().activeWindow().showMessage(
        f"Krita export probe wrote {result['png']} metadata={result['metadata_readback_ok']}",
        5000,
    )


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, ensure_ascii=False))