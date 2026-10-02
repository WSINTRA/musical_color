from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config, load_config
from common.logging_setup import setup_logging
from common.manifest import (
    Track,
    compute_track_id,
    merge_manifest,
    read_manifest,
    write_manifest,
)

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma"}


def read_audio_metadata(path: Path) -> Track | None:
    from mutagen import File as MutagenFile

    audio = MutagenFile(str(path))
    if audio is None:
        return None

    tags = audio.tags or {}

    def get_tag(*names: str) -> str | None:
        for name in names:
            if name in tags and tags[name]:
                return str(tags[name][0]).strip()
        return None

    title = get_tag("TIT2", "\xa9nam") or path.stem
    artist = get_tag("TPE1", "\xa9ART") or "Unknown Artist"
    album = get_tag("TALB", "\xa9alb") or "Unknown Album"
    genre = get_tag("TCON", "\xa9gen")
    year = get_tag("TDRC", "TYER", "\xa9day")

    track_number = None
    raw_track = get_tag("TRCK", "\xa9trk")
    if raw_track:
        part = raw_track.split("/")[0].strip()
        if part.isdigit():
            track_number = int(part)

    duration = float(audio.info.length) if audio.info else 0.0
    rel_path = str(path)

    return Track(
        track_id=compute_track_id(rel_path),
        title=title,
        artist=artist,
        album=album,
        track_number=track_number,
        duration=duration,
        source_path=rel_path,
        genre=genre,
        year=year,
    )


def scan_directory(music_dir: Path, limit: int | None = None) -> list[Track]:
    log = logging.getLogger("discover")
    tracks: list[Track] = []
    audio_files: list[Path] = []

    for path in sorted(music_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            audio_files.append(path)

    if limit:
        audio_files = audio_files[:limit]

    log.info("Found %d audio files in %s", len(audio_files), music_dir)

    for i, path in enumerate(audio_files):
        try:
            track = read_audio_metadata(path)
            if track is not None:
                tracks.append(track)
        except Exception as e:
            log.warning("Failed to read %s: %s", path, e)

        if (i + 1) % 50 == 0:
            log.info("Progress: %d/%d", i + 1, len(audio_files))

    log.info("Successfully read %d tracks", len(tracks))
    return tracks


def run(config: Config, limit: int | None = None) -> list[Track]:
    log = logging.getLogger("discover")
    manifest_path = config.output_dir / "manifest" / "tracks.jsonl"

    music_dir = config.music_dir
    if not music_dir.is_dir():
        raise FileNotFoundError(f"Music directory not found: {music_dir}")

    new_tracks = scan_directory(music_dir, limit=limit)
    existing = read_manifest(manifest_path)
    merged = merge_manifest(existing, new_tracks)

    write_manifest(merged, manifest_path)
    log.info("Manifest written to %s (%d total tracks)", manifest_path, len(merged))
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover audio files and build manifest"
    )
    parser.add_argument(
        "--config", default="pipeline/config.yaml", help="Path to config.yaml"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Process only first N files"
    )
    args = parser.parse_args()

    setup_logging("discover")
    config = load_config(args.config)
    run(config, limit=args.limit)


if __name__ == "__main__":
    main()
