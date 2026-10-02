# Musical Color

A dataset mapping music and lyrics to color selections. The core question: when a person hears a 10-15 second instrumental clip or reads a few lines of lyrics, what color do they intuitively pick?

The dataset captures that association — color, song metadata, mode (instrumental vs. lyrics), and time-to-select as a confidence signal — across a large palette (256×256 grid, ~65k colors).

## Stages

1. **Data Pipeline** — Process a local music collection into per-track bundles: a trimmed 10-15s section, vocal and instrumental stems (via demucs), a transcript (faster-whisper), and verified lyrics for that section (LRCLIB).
2. **Web App** — Interactive labeling: play a clip or show lyrics, user picks a color. React + Vite + Mantine + TypeScript (frontend), Rust + axum (backend), LadybugDB (graph database).
3. **Analysis** — Store labels in LadybugDB, compute color fingerprints per track, find clusters of color-related songs.

## Current State

The Stage 1 pipeline is working end-to-end on a 155-track collection (10 albums: Beatles, Beach Boys, Dylan, Marvin Gaye, Stones, Clash). Each track produces:

- `{track_id}.wav` — trimmed 10-15s section
- `{track_id}_vocal.mp3` / `{track_id}_instrumental.mp3` — demucs stems
- `{track_id}_transcript.txt` — faster-whisper transcription of the vocal stem
- `{track_id}_lyrics.txt` — LRCLIB-synced lyrics for the selected section

## Pipeline

```
pipeline/
├── 01_discover.py        # Walk music dir, read ID3 tags, build manifest
├── 02_select_section.py  # Pick best 10-15s window (smoothed RMS energy)
├── 03_trim.py            # ffmpeg trim to 44.1kHz stereo WAV
├── 04_separate.py        # demucs (MPS) → vocal + instrumental stems
├── 05_transcribe.py      # faster-whisper medium.en on vocal stem
├── 06_verify_lyrics.py   # LRCLIB search + timestamp-based section extraction
├── config.yaml
└── common/               # config, manifest (JSONL), logging
```

Each step is idempotent and resumable. The manifest (`data/manifest/tracks.jsonl`) is the shared contract between steps.

### Running

```bash
uv sync
uv run pipeline/01_discover.py
uv run pipeline/02_select_section.py
uv run pipeline/03_trim.py
uv run pipeline/04_separate.py
uv run pipeline/05_transcribe.py
uv run pipeline/06_verify_lyrics.py
```

### Requirements

- **Python 3.13** (managed via `uv`)
- **demucs** — external CLI in a separate Python 3.11 env (pulls in torch). Called via subprocess. Must be run with `--mp3` output flag.
- **ffmpeg** — for trimming and format conversion
- **faster-whisper** — speech-to-text on vocal stems

## Project Structure

```
├── pipeline/          # Data pipeline scripts (Python, numbered stages)
├── app/               # Web application (Stage 2)
│   ├── frontend/      # React + Vite + Mantine + TypeScript + TanStack Query
│   └── backend/       # Rust + axum + lbug (LadybugDB)
├── analysis/          # Graph queries, clustering, viz (Stage 3)
├── data/              # Raw + processed data (gitignored)
│   ├── music/         # Source audio
│   ├── manifest/      # tracks.jsonl
│   └── clips/         # Trimmed + separated audio, transcripts, lyrics
└── tests/             # Test suites
```

## Docs

- [SPEC.md](SPEC.md) — full project spec and design decisions
- [AGENTS.md](AGENTS.md) — coding conventions and workflow
- [TASK_BREAKDOWN.md](TASK_BREAKDOWN.md) — evolving task list
