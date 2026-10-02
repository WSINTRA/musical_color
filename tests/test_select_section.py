from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

PROJECT_ROOT = Path(__file__).parent.parent
MUSIC_DIR = PROJECT_ROOT / "data" / "music"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ss = _load("select_section", PROJECT_ROOT / "pipeline" / "02_select_section.py")
select_section = _ss.select_section
find_best_window = _ss.find_best_window
compute_smoothed_rms = _ss.compute_smoothed_rms


def test_section_within_bounds():
    mp3 = MUSIC_DIR / "005 The Beatles - Rubber Soul" / "04-Nowhere Man.mp3"
    start, end = select_section(str(mp3), 10, 15)
    assert start >= 0
    assert end <= 170
    duration = end - start
    assert 10 <= duration <= 15.5, f"Duration {duration} out of range"
    assert start < end


def test_section_avoids_intro_outro():
    mp3 = MUSIC_DIR / "005 The Beatles - Rubber Soul" / "04-Nowhere Man.mp3"
    start, end = select_section(str(mp3), 10, 15)
    track_duration = 169.6
    assert start >= 0.10 * track_duration, (
        f"Start {start} too early (min {0.10 * track_duration})"
    )
    assert end <= 0.85 * track_duration, (
        f"End {end} too late (max {0.85 * track_duration})"
    )


def test_known_song_picks_mid_section():
    mp3 = MUSIC_DIR / "005 The Beatles - Rubber Soul" / "04-Nowhere Man.mp3"
    start, end = select_section(str(mp3), 10, 15)
    midpoint = (start + end) / 2
    track_duration = 169.6
    assert 0.2 * track_duration < midpoint < 0.8 * track_duration, (
        f"Midpoint {midpoint:.1f}s not in the main body of the song"
    )


def test_different_songs_get_different_sections():
    file_a = MUSIC_DIR / "005 The Beatles - Rubber Soul" / "04-Nowhere Man.mp3"
    file_b = (
        MUSIC_DIR
        / "004 Bob Dylan - Highway 61 Revisited"
        / "01-Like a Rolling Stone.mp3"
    )
    start_a, end_a = select_section(str(file_a), 10, 15)
    start_b, end_b = select_section(str(file_b), 10, 15)
    assert (start_a, end_a) != (start_b, end_b)


def test_compute_smoothed_rms_shape():
    import numpy as np
    import librosa

    y, _ = librosa.load(
        str(MUSIC_DIR / "005 The Beatles - Rubber Soul" / "04-Nowhere Man.mp3"),
        sr=22050,
        mono=True,
    )
    smoothed, times = compute_smoothed_rms(y)
    assert len(smoothed) == len(times)
    assert times[0] == 0.0
    assert times[-1] < len(y) / 22050
    assert np.all(smoothed >= 0)
