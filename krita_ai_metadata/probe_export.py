from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ai_diffusion_compat import active_document as ai_active_document
from .ai_diffusion_compat import is_group_layer, is_image_layer, make_bounds
from .krita_core_adapter import active_krita_document, render_node_projection, selected_krita_nodes
from .qt_compat import QMessageBox


DEFAULT_PARAMETERS = (
    "probe export\n"
    "Negative prompt: \n"
    "Steps: 20, Sampler: probe, CFG scale: 7.0, Seed: 0, Size: 1x1, Model hash: unknown, Model: probe"
)


def active_output_dir() -> Path:
    doc = active_krita_document()
    if doc and doc.filename:
        base = Path(doc.filename).parent
    else:
        base = Path.home()
    output_dir = base / "krita_export_probe"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def active_document() -> Any:
    try:
        document = ai_active_document()
    except Exception:
        document = None
    if document is None:
        document = active_krita_document()
    if document is None:
        raise RuntimeError("No active Krita document")
    ok, message = document.check_color_mode()
    if not ok:
        raise RuntimeError(message or "Active document is not compatible")
    return document


def selected_nodes() -> list[Any]:
    return list(selected_krita_nodes())


def selected_layers(layer_manager: Any) -> list[Any]:
    layers: list[Any] = []
    for node_ref in selected_nodes():
        raw_node = getattr(node_ref, "node", node_ref)
        try:
            layers.append(layer_manager.wrap(raw_node))
        except Exception:
            continue
    return layers


def first_export_layer(layer_manager: Any) -> Any:
    selected = selected_layers(layer_manager)
    if selected:
        return selected[0]
    active = layer_manager.active
    if active is not None:
        return active
    for layer in layer_manager.all:
        if is_group_layer(layer) or is_image_layer(layer):
            return layer
    raise RuntimeError("No exportable layer found")


def export_bounds(layer: Any, fallback: Any) -> Any:
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

    if hasattr(document, "layers"):
        target = first_export_layer(document.layers)
        bounds = export_bounds(target, make_bounds(0, 0, *document.extent))
        image = target.get_pixels(bounds)
    else:
        selected = selected_nodes()
        if not selected:
            raise RuntimeError("No selected Krita node")
        target = selected[0]
        bounds = target.bounds
        image = render_node_projection(target, bounds)

    output = Path(output_dir) if output_dir is not None else active_output_dir()
    output.mkdir(parents=True, exist_ok=True)

    key = "probe"
    png_path = output / f"{key}.png"
    json_path = output / f"{key}.json"

    image.save_png_with_metadata(png_path, parameters)
    embedded = read_parameters_from_png(png_path)
    target_type = getattr(target, "type", "")

    payload = {
        "version": 1,
        "key": key,
        "target_name": target.name,
        "target_id": target.id_string,
        "target_type": str(getattr(target_type, "value", target_type)),
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
    message = f"Krita export probe wrote {result['png']} metadata={result['metadata_readback_ok']}"

    try:
        QMessageBox.information(None, "Krita AI Metadata Export", message)
    except Exception:
        print(f"[krita_ai_metadata] {message}")


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, ensure_ascii=False))