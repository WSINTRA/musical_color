# Task Breakdown

Evolving document. Tasks are grouped by stage. Each task is a committable unit of work. As we implement, this file gets updated — tasks get checked off, new tasks emerge, details get refined.

## Stage 0: Project Setup

- [ ] Init git repo, .gitignore (data/, .venv/, __pycache__/, node_modules/)
- [ ] Create project directory structure (pipeline/, app/, analysis/, data/, tests/)
- [ ] Set up Python virtualenv + requirements.txt
- [ ] Verify demucs, ffmpeg, yt-dlp are accessible from the venv

## Stage 1: Data Pipeline

### 1.1 Discover

- [ ] Locate the network SSD, confirm mount path
- [ ] Write `01_discover.py`: scan for audio files, read metadata via mutagen, build `data/manifest/tracks.jsonl`
- [ ] Test: run against a small subdirectory, verify manifest output shape
- [ ] Load Rolling Stones 500 list as a filter/priority for initial batch

### 1.2 Select Section

- [ ] Install librosa, test audio loading on a sample track
- [ ] Write `02_select_section.py`: slide window, score (energy, vocal prominence, beat alignment, novelty), pick best 10-15s
- [ ] Test: run on 3-5 known songs, verify selected sections are musically sensible (chorus/hook)
- [ ] Output: append `section_start`, `section_end` to manifest entries

### 1.3 Separate

- [ ] Write `03_separate.py`: ffmpeg trim → demucs → rename → convert to mp3
- [ ] Test: run on one track, verify output files exist and are valid audio
- [ ] Handle: already-processed tracks (skip if outputs exist)

### 1.4 Transcribe

- [ ] Install faster-whisper, verify model download works
- [ ] Write `04_transcribe.py`: load vocal stem, transcribe, save text
- [ ] Test: run on 2-3 vocal stems, verify transcription quality is acceptable
- [ ] Output: `transcription.txt` per track

### 1.5 Verify Lyrics

- [ ] Choose lyrics API/source (Genius? MusicBrainz? Other?)
- [ ] Write `05_verify_lyrics.py`: match transcription against source, store verified text + confidence score
- [ ] Test: verify 5 tracks, confirm matches are correct
- [ ] Output: `lyrics.txt` per track

### 1.6 Find Covers

- [ ] Write `06_find_covers.py`: query MusicBrainz (or chosen service) for cover versions
- [ ] Test: run on 5 well-known songs, verify cover list is sensible
- [ ] Threshold logic: 3-4 default, 6-8 for heavily covered songs
- [ ] Output: `covers.json` per track

### 1.7 Ingest Covers

- [ ] Write `07_ingest_covers.py`: yt-dlp download → transcribe full cover → align section → trim → demucs → keep vocal
- [ ] Test: ingest 2-3 covers for one song, verify vocal stems are the right section
- [ ] Output: `covers/{artist}_vocal.mp3` per track

### 1.8 Assemble

- [ ] Write `08_assemble.py`: organize final folder structure, write `meta.json` per track
- [ ] Write `run_all.py`: orchestrate all steps in order, resumable
- [ ] End-to-end test: run full pipeline on 10 songs, verify complete output structure
- [ ] Scale run: process the full initial batch

## Stage 2: Web Application

*(Tasks will be fleshed out as we get here. Tech stack not yet decided.)*

- [ ] Decide tech stack (framework, backend approach, audio serving strategy)
- [ ] Scaffold the project
- [ ] Build color palette component (256×256 canvas grid)
- [ ] Build audio player component (10s clip playback)
- [ ] Build lyrics display + cover vocal toggle
- [ ] Session flow (present item → collect color → next)
- [ ] LocalStorage tracking (bit array of seen track IDs)
- [ ] Label submission endpoint
- [ ] Audio file serving (static or API)

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
