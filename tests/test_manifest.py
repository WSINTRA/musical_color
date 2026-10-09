from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from common.manifest import (
    Track,
    compute_track_id,
    merge_manifest,
    read_manifest,
    write_manifest,
)


def make_track(tid: str = "abc123", title: str = "Test Song", **kwargs) -> Track:
    defaults = dict(
        track_id=tid,
        title=title,
        artist="Test Artist",
        album="Test Album",
        track_number=1,
        duration=120.0,
        source_path=f"/music/{tid}.mp3",
        genre="Rock",
        year="2000",
    )
    defaults.update(kwargs)
    return Track(**defaults)


def test_compute_track_id_stable():
    assert compute_track_id("/music/test.mp3") == compute_track_id("/music/test.mp3")
    assert compute_track_id("/music/test.mp3") != compute_track_id("/music/other.mp3")
    assert len(compute_track_id("/music/test.mp3")) == 12


def test_write_read_roundtrip(tmp_path: Path):
    tracks = [
        make_track("aaa111", "Song A"),
        make_track("bbb222", "Song B"),
        make_track("ccc333", "Song C", section_start=30.0, section_end=42.5),
    ]
    path = tmp_path / "tracks.jsonl"
    write_manifest(tracks, path)

    loaded = read_manifest(path)
    assert len(loaded) == 3
    assert loaded[0].track_id == "aaa111"
    assert loaded[0].title == "Song A"
    assert loaded[2].section_start == 30.0
    assert loaded[2].section_end == 42.5
    assert loaded[2].section_duration == 12.5


def test_read_nonexistent_returns_empty(tmp_path: Path):
    assert read_manifest(tmp_path / "nope.jsonl") == []


def test_merge_preserves_sections(tmp_path: Path):
    existing = [make_track("aaa111", "Song A", section_start=30.0, section_end=42.0)]
    new = [make_track("aaa111", "Song A Updated")]
    merged = merge_manifest(existing, new)
    assert len(merged) == 1
    assert merged[0].title == "Song A Updated"
    assert merged[0].section_start == 30.0
    assert merged[0].section_end == 42.0


def test_merge_adds_new_tracks(tmp_path: Path):
    existing = [make_track("aaa111")]
    new = [make_track("bbb222", "New Song")]
    merged = merge_manifest(existing, new)
    assert len(merged) == 2
    ids = {t.track_id for t in merged}
    assert ids == {"aaa111", "bbb222"}
