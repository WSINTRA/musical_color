from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from common.config import load_config


def test_load_config_defaults(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("music_dir: /tmp/music\noutput_dir: /tmp/out\n")
    cfg = load_config(cfg_file)
    assert cfg.music_dir == Path("/tmp/music")
    assert cfg.output_dir == Path("/tmp/out")
    assert cfg.clip_min_s == 10
    assert cfg.clip_max_s == 15
    assert cfg.demucs_model == "htdemucs"


def test_load_config_missing_file():
    import pytest

    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")


def test_project_config_loads():
    project_root = Path(__file__).parent.parent
    cfg = load_config(project_root / "pipeline" / "config.yaml")
    assert cfg.music_dir == Path("data/music")
    assert cfg.clip_min_s == 10
    assert cfg.clip_max_s == 15
