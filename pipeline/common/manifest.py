from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional


@dataclass
class Track:
    track_id: str
    title: str
    artist: str
    album: str
    track_number: Optional[int]
    duration: float
    source_path: str
    genre: Optional[str]
    year: Optional[str]
    section_start: Optional[float] = None
    section_end: Optional[float] = None

    @property
    def section_duration(self) -> Optional[float]:
        if self.section_start is None or self.section_end is None:
            return None
        return self.section_end - self.section_start


def compute_track_id(source_path: str) -> str:
    return hashlib.sha1(source_path.encode()).hexdigest()[:12]


def read_manifest(path: str | Path) -> list[Track]:
    path = Path(path)
    if not path.exists():
        return []
    tracks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            known = {fld.name for fld in fields(Track)}
            tracks.append(Track(**{k: v for k, v in data.items() if k in known}))
    return tracks


def write_manifest(tracks: list[Track], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for track in tracks:
            f.write(json.dumps(asdict(track)) + "\n")


def merge_manifest(existing: list[Track], new: list[Track]) -> list[Track]:
    by_id = {t.track_id: t for t in existing}
    for track in new:
        if track.track_id in by_id:
            if (
                track.section_start is None
                and by_id[track.track_id].section_start is not None
            ):
                track.section_start = by_id[track.track_id].section_start
                track.section_end = by_id[track.track_id].section_end
            by_id[track.track_id] = track
        else:
            by_id[track.track_id] = track
    return list(by_id.values())
