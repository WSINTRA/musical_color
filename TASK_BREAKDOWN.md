# Task Breakdown

Evolving document. Tasks are grouped by stage. Each task is a committable unit of work. As we implement, this file gets updated — tasks get checked off, new tasks emerge, details get refined.

## Stage 0: Project Setup

- [x] Init git repo, .gitignore (data/music/, data/clips/, .venv/, __pycache__/, node_modules/)
- [x] Create project directory structure (pipeline/, app/, analysis/, data/, tests/)
- [x] `uv init --python 3.13` — create pyproject.toml + uv-managed Python 3.13
- [x] `uv add mutagen librosa soundfile numpy pyyaml`
- [x] Fix demucs: use `--mp3` output flag to bypass broken torchcodec (torchaudio.save incompatibility)
- [x] Verify: `uv run python -c "import mutagen, librosa"` works
- [x] Verify: `demucs --help` works (pyenv 3.11, full path in config.yaml)
- [x] Verify: `ffmpeg -version` works

## Stage 1: Data Pipeline

### 1.0 Common Utilities

- [x] `pipeline/common/config.py`: load config.yaml, return frozen dataclass (music_dir, output_dir, clip_min_s, clip_max_s, demucs_model)
- [x] `pipeline/common/manifest.py`: Track dataclass, read_manifest, write_manifest, merge_manifest (JSONL)
- [x] `pipeline/common/logging_setup.py`: setup_logging(name, log_file)
- [x] `pipeline/config.yaml`: minimal config
- [x] Tests: manifest round-trip, idempotent merge, track_id stability

### 1.1 Discover

- [x] Write `01_discover.py`: walk music_dir, read ID3 via mutagen, write `data/manifest/tracks.jsonl`
- [x] Handle: skip non-audio files (.jpg, .ini), use embedded tags not folder names
- [x] Idempotent: merge with existing manifest by track_id
- [x] CLI: `--config`, `--limit N` for testing
- [x] Test: run against a small subdirectory (5 tracks), verify manifest shape
- [x] Run: full 155-track discovery

### 1.2 Select Section

- [x] Write `02_select_section.py` (v1): load via librosa, compute smoothed RMS, slide 10-15s window, pick highest-energy section in [10%, 85%] of track
- [x] Output: append `section_start`, `section_end` to manifest
- [x] Idempotent: skip tracks that already have sections
- [x] CLI: `--limit N`, `--track-id ID`
- [ ] Test: run on 3-5 known songs, listen to clips, verify musically sensible
- [ ] v2 (after listening): add spectral novelty + beat alignment to scoring
- [ ] Run: full 155-track section selection

### 1.3 Trim

- [x] Write `03_trim.py`: ffmpeg -ss/-t → 10-15s 16-bit WAV at 44.1kHz stereo → `data/clips/{track_id}.wav`
- [x] Idempotent: skip if output exists
- [x] Test: run on 3 tracks, verify file exists, correct duration
- [ ] Run: full 155-track trim

### 1.4 Separate

- [x] Write `04_separate.py`: shell out to `demucs -n htdemucs -d mps --two-stems=vocals --mp3`, rename outputs
- [x] Output: `{track_id}_vocal.mp3` + `{track_id}_instrumental.mp3`
- [x] Idempotent: skip if outputs exist
- [ ] Handle: MPS fallback to CPU if demucs fails
- [x] Test: run on 5 clips, verify outputs, listen (vocals removed)
- [ ] Run: full 155-track separation

### 1.5 Validate

- [ ] End-to-end: all 4 steps on 155 tracks
- [ ] Listen to 15-20 clips across albums/genres
- [ ] Iterate on section selection scoring if needed
- [ ] Verify demucs quality (clean vocal removal)

### 1.6 Transcribe

- [x] Install faster-whisper (medium.en, int8, CPU)
- [x] Write `05_transcribe.py`: load vocal stem, transcribe with beam_size=5, save segmented text
- [x] Test: run on 5 vocal stems, quality is "good enough" for verification (not perfect for singing)
- [x] Output: `{track_id}_transcript.txt` per track

### 1.7 Verify Lyrics

- [x] Choose lyrics source: **LRCLIB** (free, no API key, synced lyrics with per-line timestamps)
- [x] Write `06_verify_lyrics.py`: search LRCLIB by title+artist, extract section lines via timestamp matching
- [x] Test: verify 5 tracks — 4/5 matched correctly, 1 matched to a cover (same lyrics)
- [x] Output: `{track_id}_lyrics.txt` per track (section lines + full lyrics)
- [ ] Run on full 155-track batch, check coverage rate (expect some misses)

### 1.8 Find Covers (later)

- [ ] Write `07_find_covers.py`: query MusicBrainz for cover versions
- [ ] Test: run on 5 well-known songs, verify cover list is sensible
- [ ] Output: `covers.json` per track

### 1.9 Ingest Covers (later)

- [ ] Write `08_ingest_covers.py`: yt-dlp → transcribe → align → trim → demucs → keep vocal
- [ ] Test: ingest 2-3 covers for one song
- [ ] Output: `covers/{artist}_vocal.mp3` per track

### 1.10 Assemble (later)

- [ ] Write `09_assemble.py`: organize final folder structure, write `meta.json` per track
- [ ] Write `run_all.py`: orchestrate all steps in order, resumable
- [ ] End-to-end test: full pipeline on 10 songs
- [ ] Scale run: process the full collection

## Stage 1.5: Pi Scaling (after Phase 1 is validated)

- [ ] Set up Pi 5: Raspberry Pi OS 64-bit, Python 3.11+, librosa, ffmpeg
- [ ] Plug SSD into Pi, run 01-03 on Pi (overnight batch)
- [ ] Mac pulls trimmed clips from Pi, runs 04 (demucs) in batch
- [ ] manifest.jsonl is the handoff contract between Pi and Mac

## Stage 2: Web Application

Stack: React + Vite + Mantine + TS + TanStack Query (frontend), Rust + axum + lbug/LadybugDB (backend).

- [x] Decide tech stack (React/Vite/Mantine/TS/TanStack, Rust/axum, LadybugDB, Mantine ColorPicker)
- [ ] Scaffold `app/frontend/` (Vite + React + Mantine + TS + TanStack Query)
- [ ] Scaffold `app/backend/` (Rust + axum + lbug + tower-http)
- [ ] Backend: init LadybugDB schema (tracks, labels, sessions tables)
- [ ] Backend: seed tracks from `data/manifest/tracks.jsonl`
- [ ] Backend: GET `/api/tracks` — return unlabeled tracks (exclude user's seen set)
- [ ] Backend: POST `/api/labels` — submit color + timing + track_id
- [ ] Backend: serve `data/clips/` as static files
- [ ] Frontend: audio player component (HTML5, 10-15s clip)
- [ ] Frontend: lyrics display component
- [ ] Frontend: color picker (Mantine ColorPicker)
- [ ] Frontend: session flow (fetch track → present → collect color → submit → next)
- [ ] Frontend: LocalStorage tracking (bit array of seen track IDs)
- [ ] Integration: end-to-end flow (load track, play clip, pick color, submit)

## Stage 3: Storage & Analysis

*(Tasks will be fleshed out as we get here.)*

- [ ] Set up LadybugDB, define initial graph schema
- [ ] Ingest pipeline output into LadybugDB
- [ ] Color fingerprint computation
- [ ] Similarity edge computation (vector search)
- [ ] Graph visualization (interactive cluster view)

---

## Notes

- Tasks may be reordered as blockers emerge
- New tasks get added as we learn more during implementation
- A task is "done" when it's committed and the test (if any) passes
- If a task grows too large, split it into sub-tasks here
- Python managed via `uv` (3.13). Demucs is an external CLI (pyenv 3.11, called via subprocess).
