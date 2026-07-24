# Codex Project Rules

## Required reading

Before changing behaviour, read:

1. `docs/product_spec.md`
2. `docs/data_contract.md`
3. `docs/solver_contract.md`
4. `docs/objective.md`
5. `docs/acceptance_tests.md`

## Architecture rules

- Keep solver implementations behind the `RoutingSolver` interface.
- Solver modules must not import Streamlit, PyDeck, or presentation code.
- UI modules must not contain optimization logic.
- Distance and travel-time acquisition must be behind a `DistanceProvider` interface.
- Domain models must not depend on OR-Tools.
- Application code must consume solver-independent result objects.
- Do not add solver-specific fields to shared output contracts unless they are optional metadata.

## Data rules

- Use timezone-aware timestamps.
- Use integer metres for distance.
- Use integer seconds for duration.
- Use integer capacity units internally unless a future specification explicitly changes this.
- Never silently discard invalid input rows.
- Every input order must appear in the final order-results output.
- Every deferred order must include a reason or machine-readable reason code.
- Preserve the original `order_created_time` when an order is deferred.
- All random instance generation must accept and record a seed.

## Solver rules

- Every route must start and end at the assigned depot.
- Every delivered order must occur exactly once.
- No vehicle may exceed capacity.
- No route may finish after the driver's shift end.
- Travel time and service time must be included in ETA calculations.
- A solver must not report an infeasible route as successful.
- Do not claim global optimality unless it is formally proven.
- Record solver name, status, runtime, configuration, and objective components.

## Testing rules

- Every bug fix must include a regression test.
- Do not call external routing APIs from unit tests.
- Mock OSRM or any future network service.
- Add hand-verifiable tests for small instances.
- Run the full test suite before completing a task.
- Tests must cover feasible, capacity-infeasible, shift-infeasible, and mixed instances.

## Change discipline

- Prefer small, reviewable changes.
- Do not combine major refactoring with feature work unless required.
- Update relevant documentation when behaviour or schemas change.
- Preserve backward compatibility for CSV fields where practical.
- Add migration notes when a breaking schema change is unavoidable.

## Python environment

- Use uv for Python, environments, dependencies, locking, and command execution.
- Use Python 3.12 unless a documented compatibility decision changes it.
- Declare dependencies in `pyproject.toml`.
- Commit `uv.lock` and `.python-version`.
- Never commit `.venv`.
- Never install project dependencies globally.
- Run Python tools through `uv run`.
- Do not manually edit `uv.lock`.
- Run `uv lock --check` and `uv sync --locked` during final verification.
