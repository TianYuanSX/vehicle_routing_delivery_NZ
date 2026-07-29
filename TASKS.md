# Tasks

## Environment

- [x] Configure `uv`
- [x] Pin Python 3.12
- [x] Create and validate `pyproject.toml`
- [x] Generate and verify `uv.lock`
- [x] Synchronize repository-local `.venv`
- [x] Configure Ruff, Pytest, Mypy, and coverage

## Domain and input

- [x] Implement domain and result models
- [x] Implement domain and solution validation
- [x] Implement CSV and scenario loaders
- [x] Add built-in Wellington example

## Distance

- [x] Define `DistanceProvider`
- [x] Implement offline Haversine matrices
- [x] Implement injectable OSRM provider
- [x] Implement matrix cache

## Solvers

- [x] Define solver interface and registry
- [x] Implement greedy insertion baseline
- [x] Implement OR-Tools solver
- [x] Verify shared output invariants and objective scaling

## Application

- [x] Add all four input modes
- [x] Add dispatch dashboard and arbitrary-coordinate map
- [x] Add independent light/dark themes to scenario and dispatch maps
- [x] Add vehicle workloads and simulated tracking
- [x] Add CSV, YAML, and JSON exports

## Simulation

- [x] Add deterministic instance generation
- [x] Add fleet-size analysis
- [x] Add multi-day backlog simulation

## Quality and documentation

- [x] Add offline deterministic test suite
- [x] Add GitHub Actions CI
- [x] Update README and project rules
- [x] Complete implementation and acceptance reports

## Verification

- [x] `uv lock --check`
- [x] `uv sync --locked`
- [x] Python and OR-Tools import checks
- [x] Full tests and coverage
- [x] Ruff check and format check
- [x] Mypy
- [x] Wellington offline solve
- [x] Streamlit startup smoke test
- [x] Acceptance criteria review
