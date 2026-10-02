from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import librosa
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config, load_config
from common.logging_setup import setup_logging
from common.manifest import read_manifest, write_manifest

SR = 22050
HOP_LENGTH = 512
SMOOTH_WINDOW_S = 3.0
SCAN_STEP_S = 0.5


def compute_smoothed_rms(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP_LENGTH)[0]
    hop_time = HOP_LENGTH / SR
    smooth_frames = max(1, int(SMOOTH_WINDOW_S / hop_time))
    kernel = np.ones(smooth_frames) / smooth_frames
    smoothed = np.convolve(rms, kernel, mode="same")
    times = librosa.frames_to_time(np.arange(len(rms)), sr=SR, hop_length=HOP_LENGTH)
    return smoothed, times


def score_window(
    smoothed: np.ndarray,
    times: np.ndarray,
    start: float,
    end: float,
) -> float:
    mask = (times >= start) & (times < end)
    if not mask.any():
        return 0.0
    return float(np.mean(smoothed[mask]))


def find_best_window(
    y: np.ndarray,
    duration: float,
    min_s: float,
    max_s: float,
) -> tuple[float, float]:
    smoothed, times = compute_smoothed_rms(y)

    min_start = 0.10 * duration
    max_end = 0.85 * duration

    best_score = -1.0
    best_start = min_start
    best_end = min_start + min_s

    for win_dur in np.arange(min_s, max_s + 0.25, 0.5):
        win_dur = min(win_dur, max_end - min_start)
        if win_dur < min_s:
            break
        for t in np.arange(min_start, max_end - win_dur + 0.25, SCAN_STEP_S):
            t_f = float(t)
            s = score_window(smoothed, times, t_f, t_f + float(win_dur))
            if s > best_score:
                best_score = s
                best_start = t_f
                best_end = t_f + float(win_dur)

    best_end = min(best_end, duration)
    return best_start, best_end


def select_section(
    source_path: str,
    min_s: float,
    max_s: float,
) -> tuple[float, float]:
    y, _ = librosa.load(source_path, sr=SR, mono=True)
    duration = len(y) / SR
    if duration < min_s + 5:
        return 0.0, min(duration, max_s)
    return find_best_window(y, duration, min_s, max_s)


def run(config: Config, limit: int | None = None, track_id: str | None = None) -> None:
    log = logging.getLogger("select_section")
    manifest_path = config.output_dir / "manifest" / "tracks.jsonl"
    all_tracks = read_manifest(manifest_path)

    if track_id:
        targets = [t for t in all_tracks if t.track_id == track_id]
        if not targets:
            log.error("Track %s not found in manifest", track_id)
            return
    else:
        targets = all_tracks

    if limit:
        targets = targets[:limit]

    to_process = [t for t in targets if t.section_start is None]
    skipped = len(targets) - len(to_process)
    if skipped:
        log.info("Skipping %d tracks that already have sections", skipped)

    for i, track in enumerate(to_process):
        try:
            start, end = select_section(
                track.source_path, config.clip_min_s, config.clip_max_s
            )
            track.section_start = round(start, 3)
            track.section_end = round(end, 3)
            log.info(
                "[%d/%d] %s - %s: %.1fs - %.1fs (%.1fs)",
                i + 1,
                len(to_process),
                track.artist,
                track.title,
                start,
                end,
                end - start,
            )
        except Exception as e:
            log.error("Failed on %s - %s: %s", track.artist, track.title, e)

    write_manifest(all_tracks, manifest_path)
    done = sum(1 for t in all_tracks if t.section_start is not None)
    log.info("Done. %d/%d tracks have sections.", done, len(all_tracks))


def main() -> None:
    parser = argparse.ArgumentParser(description="Select best 10-15s section per track")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--track-id", type=str, default=None)
    args = parser.parse_args()

    setup_logging("select_section")
    config = load_config(args.config)
    run(config, limit=args.limit, track_id=args.track_id)


if __name__ == "__main__":
    main()
