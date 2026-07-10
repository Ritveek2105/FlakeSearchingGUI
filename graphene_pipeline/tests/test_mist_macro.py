from pathlib import Path

from pipeline_core.runtime.run_config import InputConfig, RunConfig, StitchingConfig
from pipeline_core.stages import stage1_5_stitch_tiles_mist as mist_stage


def test_mist_macro_uses_absolute_bracketed_paths(tmp_path: Path, monkeypatch):
    corrected_dir = tmp_path / "corrected tiles"
    stitched_dir = tmp_path / "stitched images"
    macro_path = tmp_path / "mist_stitch_tiles.ijm"

    monkeypatch.setattr(mist_stage, "CORRECTED_TILES_DIR", corrected_dir)
    monkeypatch.setattr(mist_stage, "STITCHED_OUTPUT_DIR", stitched_dir)
    monkeypatch.setattr(mist_stage, "MACRO_PATH", macro_path)

    config = RunConfig(
        input=InputConfig(corrected_file_pattern="{p}_corrected.tif"),
        stitching=StitchingConfig(
            grid_size_x=6,
            grid_size_y=6,
            tile_overlap=40,
            scan_order="HORIZONTALCONTINUOUS",
            grid_origin="UL",
            first_tile_index=1,
        ),
    )

    mist_stage.write_mist_macro(config)

    macro = macro_path.read_text(encoding="utf-8")

    assert f"imagedir=[{corrected_dir.resolve().as_posix()}]" in macro
    assert f"outputpath=[{stitched_dir.resolve().as_posix()}]" in macro
    assert "filenamepattern=[{p}_corrected.tif]" in macro
    assert "gridwidth=6" in macro
    assert "gridheight=6" in macro
