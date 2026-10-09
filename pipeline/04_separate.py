from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config, load_config
from common.logging_setup import setup_logging
from common.manifest import read_manifest

PAD_S = 5.0


def extract_padded(
    source_path: str,
    section_start: float,
    section_end: float,
    pad: float,
    output_path: Path,
) -> tuple[float, float]:
    clip_start = max(0.0, section_start - pad)
    clip_end = section_end + pad
    duration = clip_end - clip_start
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        str(clip_start),
        "-t",
        str(duration),
        "-i",
        source_path,
        "-ar",
        "44100",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg extract_padded failed: {result.stderr.strip()}")
    trim_offset = section_start - clip_start
    return trim_offset, duration


def trim_output(
    input_path: Path,
    offset: float,
    duration: float,
    output_path: Path,
) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        str(offset),
        "-t",
        str(duration),
        "-i",
        str(input_path),
        "-c:a",
        "libmp3lame",
        "-b:a",
        "320k",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg trim_output failed: {result.stderr.strip()}")


def run_demucs(
    clip_path: Path,
    output_dir: Path,
    demucs_path: str,
    model: str,
) -> tuple[Path, Path]:
    cmd = [
        demucs_path,
        "-n",
        model,
        "-d",
        "mps",
        "--two-stems",
        "vocals",
        "--mp3",
        "-o",
        str(output_dir),
        str(clip_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"demucs failed: {result.stderr.strip()}")

    stem = clip_path.stem
    out = output_dir / model / stem
    vocal = out / "vocals.mp3"
    instrumental = out / "no_vocals.mp3"
    if not vocal.exists() or not instrumental.exists():
        raise FileNotFoundError(f"Expected outputs missing in {out}")
    return vocal, instrumental


def run(config: Config, limit: int | None = None) -> None:
    log = logging.getLogger("separate")
    manifest_path = config.output_dir / "manifest" / "tracks.jsonl"
    clips_dir = config.output_dir / "clips"
    tracks = read_manifest(manifest_path)
    track_by_id = {t.track_id: t for t in tracks}

    clips = sorted(clips_dir.glob("*.wav"))
    clips = [c for c in clips if not c.name.endswith(("_vocal.wav", "_instrumental.wav"))]
    if limit:
        clips = clips[:limit]

    to_process = []
    for clip in clips:
        vocal_out = clip.with_name(clip.stem + "_vocal.mp3")
        instr_out = clip.with_name(clip.stem + "_instrumental.mp3")
        if not vocal_out.exists() or not instr_out.exists():
            to_process.append(clip)

    skipped = len(clips) - len(to_process)
    if skipped:
        log.info("Skipping %d clips that already have stems", skipped)

    tmp_dir = clips_dir / "_demucs_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for i, clip in enumerate(to_process):
        track_id = clip.stem
        track = track_by_id.get(track_id)
        if track is None or track.section_start is None or track.section_end is None:
            log.error(
                "[%d/%d] SKIP %s: no section in manifest",
                i + 1,
                len(to_process),
                track_id,
            )
            continue

        vocal_out = clip.with_name(clip.stem + "_vocal.mp3")
        instr_out = clip.with_name(clip.stem + "_instrumental.mp3")
        section_dur = track.section_end - track.section_start
        t0 = time.time()
        try:
            padded_path = tmp_dir / f"{track_id}_padded.wav"
            offset, padded_dur = extract_padded(
                track.source_path,
                track.section_start,
                track.section_end,
                PAD_S,
                padded_path,
            )

            vocal, instr = run_demucs(padded_path, tmp_dir, config.demucs_path, config.demucs_model)

            trim_output(vocal, offset, section_dur, vocal_out)
            trim_output(instr, offset, section_dur, instr_out)

            padded_path.unlink(missing_ok=True)
            elapsed = time.time() - t0
            log.info(
                "[%d/%d] DONE %s (%.1fs)",
                i + 1,
                len(to_process),
                clip.name,
                elapsed,
            )
        except Exception as e:
            log.error("[%d/%d] FAIL %s: %s", i + 1, len(to_process), clip.name, e)

    shutil.rmtree(tmp_dir, ignore_errors=True)

    vocals = len(list(clips_dir.glob("*_vocal.mp3")))
    instrs = len(list(clips_dir.glob("*_instrumental.mp3")))
    log.info("Done. %d vocal stems, %d instrumental stems in %s", vocals, instrs, clips_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run demucs on trimmed clips")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    setup_logging("separate")
    config = load_config(args.config)
    run(config, limit=args.limit)


if __name__ == "__main__":
    main()
