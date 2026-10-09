from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config, load_config
from common.logging_setup import setup_logging

MODEL_NAME = "medium.en"
COMPUTE_TYPE = "int8"


def transcribe_clip(
    model,
    audio_path: Path,
) -> tuple[str, list[tuple[float, float, str]]]:
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    seg_list = [(seg.start, seg.end, seg.text.strip()) for seg in segments]
    full_text = " ".join(t for _, _, t in seg_list)
    return full_text, seg_list


def run(config: Config, limit: int | None = None) -> None:
    log = logging.getLogger("transcribe")
    clips_dir = config.output_dir / "clips"

    from faster_whisper import WhisperModel

    log.info("Loading Whisper model (%s, %s)...", MODEL_NAME, COMPUTE_TYPE)
    model = WhisperModel(MODEL_NAME, device="cpu", compute_type=COMPUTE_TYPE)
    log.info("Model loaded.")

    vocal_clips = sorted(clips_dir.glob("*_vocal.mp3"))
    if limit:
        vocal_clips = vocal_clips[:limit]

    for i, clip in enumerate(vocal_clips):
        track_id = clip.stem.replace("_vocal", "")
        output_path = clips_dir / f"{track_id}_transcript.txt"
        if output_path.exists():
            log.info("[%d/%d] SKIP %s (exists)", i + 1, len(vocal_clips), track_id)
            continue

        t0 = time.time()
        try:
            full_text, seg_list = transcribe_clip(model, clip)
            with open(output_path, "w") as f:
                for start, end, text in seg_list:
                    f.write(f"[{start:.1f}-{end:.1f}] {text}\n")
                f.write(f"\n---\n{full_text}\n")
            elapsed = time.time() - t0
            log.info(
                "[%d/%d] DONE %s (%.1fs): %s",
                i + 1,
                len(vocal_clips),
                track_id,
                elapsed,
                full_text[:80],
            )
        except Exception as e:
            log.error("[%d/%d] FAIL %s: %s", i + 1, len(vocal_clips), track_id, e)

    done = len(list(clips_dir.glob("*_transcript.txt")))
    log.info("Done. %d transcripts in %s", done, clips_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe vocal stems with Whisper")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    setup_logging("transcribe")
    config = load_config(args.config)
    run(config, limit=args.limit)


if __name__ == "__main__":
    main()
