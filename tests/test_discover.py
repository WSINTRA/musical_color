from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from common.manifest import read_manifest

import importlib.util


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_discover = _load(
    "discover", Path(__file__).parent.parent / "pipeline" / "01_discover.py"
)
read_audio_metadata = _discover.read_audio_metadata
scan_directory = _discover.scan_directory

PROJECT_ROOT = Path(__file__).parent.parent
MUSIC_DIR = PROJECT_ROOT / "data" / "music"


def test_read_audio_metadata_single_file():
    mp3 = MUSIC_DIR / "005 The Beatles - Rubber Soul" / "04-Nowhere Man.mp3"
    assert mp3.exists()
    track = read_audio_metadata(mp3)
    assert track is not None
    assert track.title == "Nowhere Man"
    assert track.artist == "The Beatles"
    assert track.album == "Rubber Soul"
    assert track.track_number == 4
    assert track.duration > 100
    assert track.genre is not None
    assert len(track.track_id) == 12


def test_read_audio_metadata_handles_backtick_folder():
    mp3 = (
        MUSIC_DIR
        / "001 The Beatles - Sgt. Pepper`s Lonely Hearts Club Band"
        / "01-Sgt. Pepper's Lonely Hearts Club Band.mp3"
    )
    assert mp3.exists()
    track = read_audio_metadata(mp3)
    assert track is not None
    assert track.title == "Sgt. Pepper's Lonely Hearts Club Band"
    assert track.artist == "The Beatles"


def test_scan_directory_limit():
    tracks = scan_directory(MUSIC_DIR, limit=5)
    assert len(tracks) == 5
    for t in tracks:
        assert t.track_id
        assert t.title
        assert t.duration > 0


def test_scan_directory_full():
    tracks = scan_directory(MUSIC_DIR)
    assert len(tracks) == 155
    artists = {t.artist for t in tracks}
    assert "The Beatles" in artists
    assert "Bob Dylan" in artists
    assert "The Rolling Stones" in artists


def test_track_id_stable_across_scans():
    tracks1 = scan_directory(MUSIC_DIR, limit=10)
    tracks2 = scan_directory(MUSIC_DIR, limit=10)
    ids1 = [t.track_id for t in tracks1]
    ids2 = [t.track_id for t in tracks2]
    assert ids1 == ids2
