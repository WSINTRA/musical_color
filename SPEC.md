# Music → Color Dataset

## Concept

An experiment to build a dataset mapping music and lyrics to color selections. Explores the relationship between sound, language, and visual color as dimensions of intelligence that modern AI systems (focused on language and image generation) have largely ignored.

A user is presented with either:
- A short (~10-15s) instrumental audio clip (vocals removed)
- A sample of lyrics from a song (with optional vocal-only audio from various cover versions)

All the user does is **select a color** from a large palette (256×256 grid, ~65k colors).

The dataset captures the association between musical/lyrical content and the color a person intuitively selects, including how quickly they made the choice (confidence signal).

## Core Design Decisions

- **Lyrics are the signal** — one color per lyrics section. Audio (various vocal covers) is supportive context that helps the user decide, but the lyrics text is the anchor.
- **Instrumental clips are the signal** — the 10-15s clip itself is what the user responds to.
- **Color palette**: 256×256 grid. The exact color-space mapping (axes) will be decided during implementation.
- **Response data captured**: color (hex), song metadata, mode (instrumental/lyrics), confidence metric (time-to-select in ms), timestamp.
- **Platform**: Web-based.
- **Dataset growth**: The dataset grows over time. Returning users only see net-new content.
- **Storage**: LadybugDB (embedded graph database, formerly Kuzu) for song relationships, labels, and vector-based color similarity.
- **Scale target**: 10k+ songs. The architecture should support this from the start.

## Stage 1: Data Pipeline

The immediate focus. Building the initial dataset from a local music collection.

### Source

- Large local music collection on an external SSD (on the local network)
- Seed list: Rolling Stones 500 Greatest Albums
- Collection naming is mixed/unstructured — rely on embedded metadata (ID3/Vorbis) as source of truth

### Available Tools (on build machine: Mac Studio, M2 Ultra, 64GB)

- `demucs` — vocal/instrumental separation
- `ffmpeg` — audio trimming, format conversion
- `python3` (3.14 via pyenv)
- `yt-dlp` — downloading cover versions
- `faster-whisper` — speech-to-text on vocal stems (to be installed)
- `librosa` — audio feature extraction for section selection (to be installed)

### Pipeline Steps

1. **Discover** — Locate audio files on the network SSD. Build a manifest of tracks with normalized metadata.
2. **Select Section** — Auto-pick the best 10-15s window per track using audio heuristics (energy, vocal prominence, beat alignment, spectral novelty).
3. **Separate** — Trim the section, run demucs to get instrumental + vocal stem.
4. **Transcribe** — Run STT on the vocal stem to get the lyrics text for that section.
5. **Verify Lyrics** — Match transcription against a lyrics API to confirm track identity and get clean text.
6. **Find Covers** — Use MusicBrainz (or similar) to find 3-8 cover versions.
7. **Ingest Covers** — Download covers via yt-dlp, align to the same lyric section, demucs, keep vocal stems only.
8. **Assemble** — Bundle into a clean per-track folder structure with metadata.

### Output Structure (per track)

```
tracks/{track_id}/
├── meta.json            # title, artist, album, year, genre, key, tempo, section timing
├── instrumental.mp3     # 10-15s, vocals removed
├── vocal_stem.mp3       # 10-15s, vocals only (original artist)
├── lyrics.txt           # verified lyrics for this section
└── covers/
    ├── {artist_1}_vocal.mp3
    ├── {artist_2}_vocal.mp3
    └── ...
```

### Pipeline Principles

- Each step is idempotent and resumable (check if output exists before re-processing)
- The pipeline runs incrementally — add songs over time, don't reprocess everything
- Scripts live in `pipeline/` as numbered stages
- Configuration in a single `pipeline/config.yaml`

## Stage 2: Web Application (Directional — Not Yet Decided)

The interactive app where users encounter clips/lyrics and select colors.

**Decided:**
- Web-based
- 256×256 color grid (canvas-based picker)
- HTML5 audio for clip playback
- LocalStorage for tracking which tracks a user has already labeled (bit array)
- Dataset grows over time — users get net-new content each visit
- Confidence metric = time from palette activation to selection

**Not yet decided (will be determined during implementation):**
- Specific frontend framework
- Backend architecture
- How audio files are served at scale
- Exact color-space mapping for the palette axes
- Session length / batching strategy
- Deployment target

## Stage 3: Data Storage & Analysis (Directional)

**Decided:**
- LadybugDB (embedded graph DB) for storage
- Songs as nodes, labels as related nodes, similarity as computed edges
- Color "fingerprint" per track (aggregate of user color assignments)
- Vector similarity for finding clusters of color-related songs
- Visualization: interactive graph showing clusters

**Not yet decided:**
- Exact graph schema
- Fingerprint algorithm (mean color? histogram? distribution?)
- Visualization tooling
- When/how similarity edges are recomputed

## Open Questions

- Lyrics API choice (Genius, MusixMatch, MusicBrainz + scraping?)
- Network SSD location/mount
- Python environment setup (virtualenv location, package management)
- Whether to extract musical metadata (key, tempo) via librosa or rely on tags
- Legal/licensing considerations for serving cover versions downloaded via yt-dlp
