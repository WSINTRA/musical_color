from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config, load_config
from common.logging_setup import setup_logging
from common.manifest import read_manifest, write_manifest


def trim_clip(
    source_path: str,
    start: float,
    duration: float,
    output_path: Path,
) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        str(start),
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
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")


def run(config: Config, limit: int | None = None) -> None:
    log = logging.getLogger("trim")
    manifest_path = config.output_dir / "manifest" / "tracks.jsonl"
    clips_dir = config.output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    tracks = read_manifest(manifest_path)
    tracks_with_sections = [
        t for t in tracks if t.section_start is not None and t.section_end is not None
    ]

    if limit:
        tracks_with_sections = tracks_with_sections[:limit]

    for i, track in enumerate(tracks_with_sections):
        assert track.section_start is not None and track.section_end is not None
        output_path = clips_dir / f"{track.track_id}.wav"
        if output_path.exists():
            log.info(
                "[%d/%d] SKIP %s - %s (exists)",
                i + 1,
                len(tracks_with_sections),
                track.artist,
                track.title,
            )
            continue

        duration = track.section_end - track.section_start
        try:
            trim_clip(track.source_path, track.section_start, duration, output_path)
            log.info(
                "[%d/%d] TRIM %s - %s: %.1fs-%.1fs (%.1fs) -> %s",
                i + 1,
                len(tracks_with_sections),
                track.artist,
                track.title,
                track.section_start,
                track.section_end,
                duration,
                output_path.name,
            )
        except Exception as e:
            log.error(
                "[%d/%d] FAIL %s - %s: %s",
                i + 1,
                len(tracks_with_sections),
                track.artist,
                track.title,
                e,
            )

    done = len(list(clips_dir.glob("*.wav")))
    log.info("Done. %d clips in %s", done, clips_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trim audio to selected sections")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    setup_logging("trim")
    config = load_config(args.config)
    run(config, limit=args.limit)


if __name__ == "__main__":
    main()
