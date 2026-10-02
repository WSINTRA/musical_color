# AGENTS.md

## Code Discipline

This project is built incrementally. Each task produces a committable chunk of working code. Quality over speed — the dataset and pipeline will be run many times as the collection grows, so the code must be maintainable and predictable.

## TDD Mindset

- **Write the test first** for any non-trivial logic (section selection heuristics, lyrics matching, data transformation, API parsing).
- For pipeline scripts: write a small test fixture (a 10s audio clip, a sample manifest entry) and assert the output shape/content before wiring up the full run.
- For the web app: component tests for the color picker, audio player, and session flow. Integration test for the label submission endpoint.
- It's fine to skip tests for thin glue code (a script that just calls demucs with the right args). Test the logic, not the plumbing.
- Tests live alongside source or in a `tests/` directory mirroring the structure.

## Code Hygiene

### Python (Pipeline)

- **Small functions**. If a function does more than one thing, split it.
- **No dead code**. Don't leave commented-out blocks. Git remembers.
- **Explicit over clever**. Prefer readable, boring code. The pipeline will be debugged at 1am when a batch of 500 tracks fails at step 6.
- **Type hints** on all Python functions. Typed parameters, typed returns.
- **Error handling at boundaries**. Validate inputs at the edge of each pipeline step. Fail fast with a clear message. Don't let a bad file path propagate three steps downstream.
- **No global mutable state**. Pipeline steps receive config as parameters, not from a shared module-level dict.
- **Logging, not print**. Use Python's `logging` module in pipeline scripts. Structured enough to grep, simple enough to read.

### TypeScript (Frontend)

- **Type-safe by default**. Use TypeScript strict mode. No `any` unless there's no alternative.
- **Components are small and focused**. One component, one job. Compose them.
- **Server state via TanStack Query**. Don't store API responses in React state. Use `useQuery` / `useMutation` with proper cache keys.
- **Client state via local state or URL params**. Don't reach for a state library for this app's scope.
- **Mantine components** for UI. Don't hand-roll a button or input when Mantine has one. Reference: https://mantine.dev/llms/core-package.md

### Rust (Backend)

- **Idiomatic Rust**. Use `Result<T, E>` for error propagation. No panics in request handlers.
- **Small modules**. `main.rs` sets up the server. Routes, DB, and models get their own modules.
- **Serde** for all JSON serialization. Use `Deserialize` on request bodies, `Serialize` on responses.
- **`lbug` crate** for LadybugDB access (v0.19.0+). Cypher queries as string constants, not interpolated SQL. Reference: https://github.com/LadybugDB/ladybug-skill/blob/main/reference/rust-interface.md
- **Tests in `#[cfg(test)]` modules** alongside the code. Integration tests in `tests/`.

## Project Structure

```
DATASET_IDEA/
├── pyproject.toml          # uv project config + dependencies (Python)
├── uv.lock                 # Lock file (committed for reproducibility)
├── SPEC.md                 # What we're building and why
├── AGENTS.md               # This file — how we build it
├── TASK_BREAKDOWN.md       # Evolving task list
├── pipeline/               # Data pipeline scripts (Python)
│   ├── config.yaml
│   ├── common/             # Shared utilities (logging, config loading, IO)
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── manifest.py
│   │   └── logging_setup.py
│   ├── 01_discover.py
│   ├── 02_select_section.py
│   ├── 03_trim.py
│   ├── 04_separate.py
│   ├── 05_transcribe.py
│   ├── 06_verify_lyrics.py
│   └── run_all.py
├── app/                    # Web application (Stage 2)
│   ├── frontend/           # React + Vite + Mantine + TS + TanStack Query
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── index.html
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx
│   │       ├── components/
│   │       └── lib/
│   └── backend/            # Rust + axum + lbug (LadybugDB)
│       ├── Cargo.toml
│       └── src/
│           ├── main.rs
│           ├── db.rs
│           ├── routes.rs
│           └── models.rs
├── analysis/               # Graph queries, clustering, viz (Stage 3)
├── data/                   # Raw + processed data (gitignored)
│   ├── music/              # Source audio (gitignored)
│   ├── manifest/
│   ├── clips/              # Trimmed + separated audio
│   └── tracks/             # Final per-track bundles
└── tests/                  # Python test suites
```

## Commits

- Each task from TASK_BREAKDOWN.md is one or more commits.
- Commit message format: `{step}: {what changed}` (e.g., `03-separate: add mp3 conversion after demucs`)
- Don't commit data files (audio, large JSON). `.gitignore` handles this.
- A commit should represent a working state. If the pipeline was working before your commit and still works after, you're good.

## Dependencies

### Python (Pipeline)

- Managed via `uv`. Project uses Python 3.13 (uv-managed). The `.venv/` is created and maintained by `uv`.
- `pyproject.toml` for dependencies, `uv.lock` for reproducible installs. Use `uv add` / `uv remove` to manage packages.
- Run pipeline scripts with `uv run pipeline/01_discover.py` (or equivalent).
- **Demucs** is an external CLI tool installed in a separate pyenv 3.11 environment (it pulls in torch). Pipeline scripts call it via `subprocess`. Do NOT install torch/demucs in the project venv.

### TypeScript (Frontend)

- `app/frontend/package.json` — managed via npm.
- Key deps: `react`, `react-dom`, `@mantine/core`, `@mantine/hooks`, `@tanstack/react-query`, `vite`, `typescript`.
- Run with `npm run dev` from `app/frontend/`.

### Rust (Backend)

- `app/backend/Cargo.toml` — managed via cargo.
- Key deps: `axum`, `lbug` (LadybugDB), `tokio`, `serde`, `serde_json`, `tower-http` (static files, CORS), `tracing` (logging).
- Run with `cargo run` from `app/backend/`.

### LadybugDB

- Embedded graph database, Cypher dialect. The `lbug` crate (v0.19.0) is the Rust interface.
- The database file lives at `data/music_color.lbdb` (gitignored).
- Reference docs: https://github.com/LadybugDB/ladybug-skill (shell, Python, JS, Rust interfaces).
- The LadybugDB agent skill is at: https://github.com/LadybugDB/ladybug-skill/blob/main/SKILL.md

## Things We Don't Do

- No premature abstraction. Don't build a plugin system for section selection heuristics when we have one heuristic.
- No config files with 50 options. Keep `config.yaml` minimal. Add options when you actually need them.
- No "temporary" code that stays for 3 commits. If it's a hack, mark it with a TODO and a task reference, and either fix it next or remove it.
- No mixing concerns in one file. The section selection logic doesn't belong in the demucs script.
- No hand-rolling UI components when Mantine has one.
- No `any` in TypeScript. No `unwrap()` in production Rust code paths.
