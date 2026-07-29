# Implementation Report

## Executive summary

The documentation-only starting repository is now a runnable static capacitated
vehicle-routing and dispatch prototype. It has a reproducible Python 3.12 `uv`
environment, strict shared contracts, validated input, two interchangeable solvers,
offline/OSRM distance adapters, synthetic Wellington data, a Streamlit application,
exports, deterministic fleet and multi-day simulations, CI, and an offline test suite.

## Initial audit and migration

The repository initially contained `AGENTS.md`, `README.md`, and six Markdown files
under `docs/`. It had no Python source, dependency or lock configuration, tests,
application, example data, lint/type configuration, CI, or legacy requirements to
migrate. The directory was initially not a Git worktree, so prior history could not
be inspected. Git was subsequently initialized for publication. Useful product
documentation was retained and linked from the expanded README.

`uv` was not installed. The official Linux release binary was downloaded from
Astral's GitHub releases into ignored `.tools/`, then used to install/manage Python
3.12.13 and create the ignored repository-local `.venv`.

## Implemented features

- Frozen solver-independent domain and result dataclasses with timezone, coordinate,
  capacity, shift, matrix, ID, cost, priority, and objective validation.
- Whole-file CSV/YAML loading with aggregated row errors, dataframe adapters,
  cross-reference checks, and no silent row loss.
- Deterministic Haversine distance/time matrices, injectable OSRM table HTTP client,
  readable content-addressed JSON cache, and UI Haversine fallback.
- Common `RoutingSolver` protocol and registry.
- Deterministic greedy oldest/highest-priority cheapest feasible insertion.
- OR-Tools routing adapter with capacity and time dimensions, per-vehicle capacity
  and shift bounds, service-aware transit, optional drops, age/priority penalties,
  flow-time pressure, configurable strategies, and time limit.
- Shared route/ETA/result construction, objective metrics, operating costs,
  deferred-reason diagnosis, and solution invariant validation.
- Synthetic Wellington demand at ten geocoded public locations, with address-source
  and coordinate provenance documented beside the dataset.
- Seeded arbitrary instance generation.
- Streamlit built-in/upload/manual/generated inputs, solver/distance/objective
  settings, overview, auto-fit map, workloads, simulated statuses, fleet analysis,
  charts, and CSV/JSON/YAML exports.
- Reproducible fleet-size and day-by-day backlog simulation.
- GitHub Actions checks for lock, sync, tests, Ruff, formatting, and Mypy.

## Repository structure

Application entry is `app.py`; package code is under `src/vrp_demo` in `domain`,
`io`, `distance`, `solvers`, `dispatch`, `simulation`, and `presentation` layers.
Synthetic data is under `data/wellington`, tests under `tests`, and CI under
`.github/workflows`.

## Environment

- Python: 3.12.13 (project constraint `>=3.12,<3.13`)
- `uv`: 0.11.31
- Build backend: `uv_build`, selected because the project is a new pure-Python
  package and the installed `uv` supports its native backend.
- Runtime dependencies: httpx 0.28.1, OR-Tools 9.15.6755, pandas 2.3.3,
  Plotly 6.9.0, PyDeck 0.9.3, PyYAML 6.0.3, Streamlit 1.60.0.
- Development dependencies: pytest 8.4.2, pytest-cov 6.3.0, Ruff 0.15.22,
  Mypy 1.20.2, pandas-stubs, and types-PyYAML.

## Solver and objective design

Both implementations receive exactly the same immutable `RoutingInstance`, including
integer metre/second matrices, and return the same `RoutingSolution`. Route timing is
built once outside solver adapters to keep ETA and metrics consistent.

Business objective reporting is:

```text
deferred cost + total-flow-time cost + total-distance cost
```

Drop cost includes base non-delivery, full age days from the original creation time,
and priority. OR-Tools applies those drop penalties and minimizes arrival cumul
variables in seconds while distance is an arc cost. The reported objective is
recomputed in documented business units from the extracted solution. This is a
weighted approximation to lexicographic intent and is never presented as a proof of
global optimality.

## Verification results

- Tests: 44 passed, including reactive-map coverage across all four input modes,
  manual-table compatibility, editable depot conversion, and the validated
  three-table input bundle.
- Coverage: 90% total with branch measurement.
- Ruff check: passed.
- Ruff format check: passed.
- Mypy strict package check: passed with no issues across 33 source files.
- Wellington offline solve: passed with both solvers; each planned 9 and deferred 1.
- Generated 50-order/10-vehicle greedy smoke: feasible, 46 planned, 4 deferred,
  0.005 seconds wall time.
- Streamlit server smoke: started on localhost and shut down by the timeout.
- Streamlit AppTest: all four input modes, all three Manual tables, reactive
  generated/uploaded map data, stale-result invalidation, and the default
  Wellington solve completed with zero exceptions.
- Lock check and locked sync: passed.
- OR-Tools import: passed.
- Acceptance mapping: [docs/acceptance_results.md](docs/acceptance_results.md).

## Important assumptions

See [ASSUMPTIONS.md](ASSUMPTIONS.md). The key choices are integer cartons, 35 km/h
default offline speed, five-minute default service, route departure at the later of
shift start/cutoff, and the documented default objective weights.

## Conflicts and resolutions

No meaningful conflict was found. Existing documents allow Python 3.12 or newer;
the explicit task pins 3.12. The requested OSRM preference for route geometry cannot
be satisfied by the table endpoint alone, so OSRM road matrices are used while the
map transparently labels straight visualization segments.

## Known limitations

- OR-Tools uses a weighted single-pass approximation rather than formal
  lexicographic sequential optimization.
- OSRM table results do not provide route geometry; map segments remain straight.
- The multi-day simulator is a tested application API, not a dedicated Streamlit
  page in this first vertical slice.
- No live traffic/GPS, time windows, breaks, reloading, multiple trips/depots,
  split deliveries, or multiple capacity dimensions.
- The UI catches and logs solver/provider errors but does not persist operational
  logs or solution history.

## Blockers and Git

No blocker remains. Git was initialized after implementation for the initial
publication. No secrets, `.venv`, cache, local editor completion index, or local
tool binary is included in tracked project files.

## Human review and next steps

Review objective calibration against realistic maximum route scales, confirm the
capacity unit and service policy, select an OSRM hosting/privacy policy, and inspect
the visual design in a browser. Next technical steps are OSRM route geometry,
strict multi-pass lexicographic solving, a multi-day UI, persisted plans/events,
and production authentication/deployment controls.
