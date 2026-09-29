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

- **Small functions**. If a function does more than one thing, split it.
- **No dead code**. Don't leave commented-out blocks. Git remembers.
- **Explicit over clever**. Prefer readable, boring code. The pipeline will be debugged at 1am when a batch of 500 tracks fails at step 6.
- **Type hints** on all Python functions. Typed parameters, typed returns.
- **Error handling at boundaries**. Validate inputs at the edge of each pipeline step. Fail fast with a clear message. Don't let a bad file path propagate three steps downstream.
- **No global mutable state**. Pipeline steps receive config as parameters, not from a shared module-level dict.
- **Logging, not print**. Use Python's `logging` module in pipeline scripts. Structured enough to grep, simple enough to read.

## Project Structure

```
DATASET_IDEA/
├── SPEC.md                 # What we're building and why
├── AGENTS.md               # This file — how we build it
├── TASK_BREAKDOWN.md       # Evolving task list
├── pipeline/               # Data pipeline scripts
│   ├── config.yaml
│   ├── common/             # Shared utilities (logging, config loading, IO)
│   ├── 01_discover.py
│   ├── 02_select_section.py
│   ├── ...
│   └── run_all.py
├── app/                    # Web application (Stage 2)
├── analysis/               # Graph queries, clustering, viz (Stage 3)
├── data/                   # Raw + processed data (gitignored)
│   ├── manifest/
│   └── tracks/
└── tests/                  # Test suites
```

## Commits

- Each task from TASK_BREAKDOWN.md is one or more commits.
- Commit message format: `{step}: {what changed}` (e.g., `03-separate: add mp3 conversion after demucs`)
- Don't commit data files (audio, large JSON). `.gitignore` handles this.
- A commit should represent a working state. If the pipeline was working before your commit and still works after, you're good.

## Dependencies

- Python: managed via `pyenv` (3.14). Use a project-level virtualenv in `.venv/`.
- Package management: `pip` with a `requirements.txt` (or `pyproject.toml` if we adopt a build system later).
- Pin versions for reproducibility. The pipeline must produce the same output given the same input.
- Node.js dependencies: `package.json` in `app/` when we get there.

## Things We Don't Do

- No premature abstraction. Don't build a plugin system for section selection heuristics when we have one heuristic.
- No config files with 50 options. Keep `config.yaml` minimal. Add options when you actually need them.
- No "temporary" code that stays for 3 commits. If it's a hack, mark it with a TODO and a task reference, and either fix it next or remove it.
- No mixing concerns in one file. The section selection logic doesn't belong in the demucs script.
