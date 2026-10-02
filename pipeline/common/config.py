from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Config:
    music_dir: Path
    output_dir: Path
    clip_min_s: float
    clip_max_s: float
    demucs_model: str
    demucs_path: str


def load_config(path: str | Path = "pipeline/config.yaml") -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        raw = yaml.safe_load(f)

    return Config(
        music_dir=Path(raw["music_dir"]),
        output_dir=Path(raw["output_dir"]),
        clip_min_s=float(raw.get("clip_min_s", 10)),
        clip_max_s=float(raw.get("clip_max_s", 15)),
        demucs_model=raw.get("demucs_model", "htdemucs"),
        demucs_path=raw.get("demucs_path", "demucs"),
    )
