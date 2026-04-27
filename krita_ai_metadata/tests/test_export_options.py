from pathlib import Path

from krita_ai_metadata.export_options import ExportOptions
from krita_ai_metadata.export_target_scanner import ExportMode
from krita_ai_metadata.ui.export_dialog import ExportDialogConfig


def test_defaults_are_png_manifest_selected_mode(tmp_path: Path) -> None:
    options = ExportOptions(output_dir=tmp_path, selected_layer_ids=["layer-1"])

    assert options.mode == ExportMode.selected
    assert options.overwrite is False
    assert options.allow_unresolved is False
    assert options.write_manifest is True
    assert options.include_invisible_targets is False
    assert options.image_extension == "png"
    assert options.validate() == []


def test_to_dialog_config_maps_only_fallback_fields(tmp_path: Path) -> None:
    options = ExportOptions(
        output_dir=tmp_path,
        mode=ExportMode.all,
        selected_layer_ids=["docker-only-layer"],
        overwrite=True,
        allow_unresolved=True,
        write_manifest=False,
        include_invisible_targets=True,
    )

    config = options.to_dialog_config()

    assert isinstance(config, ExportDialogConfig)
    assert config.output_dir == tmp_path
    assert config.mode == ExportMode.all
    assert config.overwrite is True
    assert config.allow_unresolved is True
    assert config.write_manifest is False
    assert not hasattr(config, "selected_layer_ids")
    assert not hasattr(config, "include_invisible_targets")


def test_validate_rejects_non_png_and_empty_selection(tmp_path: Path) -> None:
    options = ExportOptions(
        output_dir=tmp_path,
        image_extension="jpeg",
        mode=ExportMode.selected,
        selected_layer_ids=[],
    )

    warnings = options.validate()

    assert "Only PNG export is supported in v1.1." in warnings
    assert "No docker layer selection is set." in warnings


def test_normalized_selected_layer_ids_removes_empty_and_duplicates(tmp_path: Path) -> None:
    options = ExportOptions(
        output_dir=tmp_path,
        selected_layer_ids=["", "layer-1", "layer-1", "layer-2", ""],
    )

    assert options.normalized_selected_layer_ids() == ["layer-1", "layer-2"]


def test_visible_mode_does_not_require_selected_ids(tmp_path: Path) -> None:
    options = ExportOptions(
        output_dir=tmp_path,
        mode=ExportMode.visible,
        selected_layer_ids=[],
    )

    assert "No docker layer selection is set." not in options.validate()