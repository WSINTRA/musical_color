from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config, load_config
from common.logging_setup import setup_logging
from common.manifest import read_manifest

LRCLIB_API = "https://lrclib.net/api"
REQUEST_DELAY_S = 0.5


def _api_search(params: dict) -> list[dict]:
    url = f"{LRCLIB_API}/search?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "dataset-idea/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _artist_match(result_artist: str, target_artist: str) -> bool:
    a, b = result_artist.lower(), target_artist.lower()
    return a == b or a in b or b in a


def search_lyrics(title: str, artist: str, album: str = "") -> dict | None:
    base = {"q": title, "artist_name": artist}

    if album:
        results = _api_search({**base, "album_name": album})
        if results:
            for r in results:
                if _artist_match(r.get("artistName", ""), artist):
                    return r
            return results[0]

    results = _api_search(base)
    if results:
        for r in results:
            if _artist_match(r.get("artistName", ""), artist):
                return r
        return results[0]

    return None


def parse_synced_lyrics(synced: str) -> list[dict]:
    lines = []
    pattern = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)")
    for raw_line in synced.split("\n"):
        m = pattern.match(raw_line.strip())
        if m:
            mins, secs, ms, text = m.groups()
            if not text.strip():
                continue
            timestamp = int(mins) * 60 + int(secs) + int(ms.ljust(3, "0")) / 1000
            lines.append({"time": timestamp, "text": text.strip()})
    return lines


def extract_section_lines(
    lines: list[dict],
    section_start: float,
    section_end: float,
) -> list[str]:
    matched = [line["text"] for line in lines if section_start <= line["time"] < section_end]
    if not matched:
        nearest = min(lines, key=lambda line: abs(line["time"] - section_start)) if lines else None
        if nearest:
            idx = lines.index(nearest)
            matched = [lines[idx]["text"]]
    return matched


def run(config: Config, limit: int | None = None) -> None:
    log = logging.getLogger("verify_lyrics")
    manifest_path = config.output_dir / "manifest" / "tracks.jsonl"
    clips_dir = config.output_dir / "clips"
    tracks = read_manifest(manifest_path)

    tracks_with_sections = [
        t for t in tracks if t.section_start is not None and t.section_end is not None
    ]
    if limit:
        tracks_with_sections = tracks_with_sections[:limit]

    for i, track in enumerate(tracks_with_sections):
        assert track.section_start is not None and track.section_end is not None
        output_path = clips_dir / f"{track.track_id}_lyrics.txt"
        if output_path.exists():
            log.info(
                "[%d/%d] SKIP %s - %s (exists)",
                i + 1,
                len(tracks_with_sections),
                track.artist,
                track.title,
            )
            continue

        log.info(
            "[%d/%d] LOOKUP %s - %s (%.0f-%.0fs)",
            i + 1,
            len(tracks_with_sections),
            track.artist,
            track.title,
            track.section_start,
            track.section_end,
        )

        result = search_lyrics(track.title, track.artist, track.album)
        if result is None:
            log.warning(
                "[%d/%d] NOT FOUND %s - %s",
                i + 1,
                len(tracks_with_sections),
                track.artist,
                track.title,
            )
            continue

        synced = result.get("syncedLyrics")
        plain = result.get("plainLyrics", "")
        matched_artist = result.get("artistName", "")

        if synced:
            lines = parse_synced_lyrics(synced)
            section_lines = extract_section_lines(lines, track.section_start, track.section_end)
        else:
            section_lines = []
            log.warning(
                "No synced lyrics for %s - %s, falling back to plain",
                track.artist,
                track.title,
            )

        with open(output_path, "w") as f:
            f.write(f"# {track.artist} - {track.title}\n")
            f.write(f"# Album: {track.album}\n")
            f.write(f"# LRCLIB artist: {matched_artist}\n")
            f.write(f"# Section: {track.section_start:.1f}s - {track.section_end:.1f}s\n")
            f.write(f"# Matched lines: {len(section_lines)}\n\n")
            f.write("=== SECTION LYRICS ===\n")
            for line in section_lines:
                f.write(line + "\n")
            f.write("\n=== FULL LYRICS ===\n")
            f.write((plain or "(no plain lyrics available)") + "\n")

        log.info(
            "[%d/%d] DONE %s - %s: %d section lines (artist: %s)",
            i + 1,
            len(tracks_with_sections),
            track.artist,
            track.title,
            len(section_lines),
            matched_artist,
        )
        time.sleep(REQUEST_DELAY_S)

    done = len(list(clips_dir.glob("*_lyrics.txt")))
    log.info("Done. %d lyric files in %s", done, clips_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Look up and extract lyrics sections")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    setup_logging("verify_lyrics")
    config = load_config(args.config)
    run(config, limit=args.limit)


if __name__ == "__main__":
    main()
