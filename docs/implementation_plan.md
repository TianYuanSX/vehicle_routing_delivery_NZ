# Implementation Plan for Codex

## 1. Recommended repository structure

```text
vehicle-routing-demo/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── app.py
├── docs/
│   ├── product_spec.md
│   ├── data_contract.md
│   ├── solver_contract.md
│   ├── objective.md
│   ├── acceptance_tests.md
│   └── implementation_plan.md
├── data/
│   └── wellington/
│       ├── orders.csv
│       ├── vehicles.csv
│       ├── depots.csv
│       └── scenario.yaml
├── src/vrp_demo/
│   ├── domain/
│   │   ├── models.py
│   │   ├── enums.py
│   │   └── validation.py
│   ├── io/
│   │   ├── csv_loader.py
│   │   ├── scenario_loader.py
│   │   └── example_data.py
│   ├── distance/
│   │   ├── base.py
│   │   ├── haversine.py
│   │   ├── osrm.py
│   │   └── cache.py
│   ├── solvers/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── greedy_insertion.py
│   │   └── ortools_cvrp.py
│   ├── dispatch/
│   │   ├── planner.py
│   │   ├── eta.py
│   │   └── result_builder.py
│   ├── simulation/
│   │   ├── multi_day.py
│   │   ├── fleet_size.py
│   │   └── instance_generator.py
│   └── presentation/
│       ├── map_layers.py
│       ├── metrics.py
│       └── exports.py
└── tests/
    ├── test_validation.py
    ├── test_haversine.py
    ├── test_greedy_solver.py
    ├── test_ortools_solver.py
    ├── test_eta.py
    ├── test_multi_day.py
    └── test_fleet_simulation.py
```

## 2. Build sequence

### Phase 1 — Scaffold and domain model

Goal: create a stable foundation without solver or UI logic.

Codex task:

```text
Read AGENTS.md and all files under docs/.

Create the Python package structure described in docs/implementation_plan.md.
Implement Order, Vehicle, Depot, RoutingInstance, SolverConfig,
RoutingSolution, validation errors, and CSV-loading models.

Use timezone-aware timestamps and integer metres/seconds internally.
Add tests for valid and invalid input.
Do not implement a solver or Streamlit UI yet.
Run the full test suite and fix all failures.
```

### Phase 2 — Distance layer

Goal: isolate geographic calculations and network routing.

Codex task:

```text
Implement the DistanceProvider protocol.

Add:
1. a deterministic Haversine provider for offline use;
2. an OSRM provider for road distance and duration matrices;
3. a file cache keyed by coordinates and provider settings.

External network calls must be mocked in tests.
Do not add solver logic or Streamlit code.
```

### Phase 3 — Baseline solver

Goal: create a transparent benchmark before OR-Tools.

Codex task:

```text
Implement GreedyInsertionSolver behind RoutingSolver.

Requirements:
- oldest order first, then priority;
- cheapest feasible insertion;
- capacity and shift feasibility;
- travel and service duration in route timing;
- explicit deferred orders and reasons;
- deterministic behaviour for a fixed seed;
- optional 2-opt route improvement.

Add hand-verifiable tests and invariant checks.
```

### Phase 4 — OR-Tools solver

Goal: implement the main optimization solver without changing shared contracts.

Codex task:

```text
Implement ORToolsCVRPSolver behind RoutingSolver.

Requirements:
- distance arc cost;
- capacity dimension;
- time dimension;
- per-vehicle shift bounds;
- one start and one end depot per vehicle;
- optional order dropping with age- and priority-based penalties;
- total flow-time cost;
- configurable first solution strategy;
- configurable local search metaheuristic;
- configurable time limit;
- extraction of routes, ETAs, departure times, deferred orders, and metrics.

Do not expose OR-Tools objects outside the adapter.
Compare output invariants with the baseline solver.
```

### Phase 5 — Result validation

Goal: prevent invalid solver results from reaching the UI.

Codex task:

```text
Create a solution validator that checks every invariant in
`docs/solver_contract.md`.

Run it automatically after every solver call in development and tests.
Return clear diagnostics for duplicate orders, capacity violations,
shift violations, inconsistent timestamps, and metric mismatches.
```

### Phase 6 — Streamlit application

Goal: provide the main demonstration experience.

Codex task:

```text
Implement a Streamlit application using the existing domain,
distance, solver, and result interfaces.

Add:
- built-in Wellington example;
- CSV uploads;
- manual editable tables;
- generated instances;
- validation messages;
- solver selector and settings;
- dispatch summary;
- map routes and order markers;
- order-results table;
- vehicle workload page;
- CSV exports.

Do not duplicate optimization or ETA logic in the UI.
Map bounds must fit the input coordinates automatically.
```

### Phase 7 — Fleet-size simulation

Goal: demonstrate the relationship between capacity, service, and cost.

Codex task:

```text
Implement fleet-size scenario analysis.

For each requested fleet size:
- use the same orders and planning time;
- use the same distance and duration matrices;
- use the same objective weights;
- use the same solver time limit and seed;
- record all KPIs in a tidy dataframe.

Add plots for delivered orders, deferred orders, total distance,
mean and maximum flow time, utilization, vehicles used, and runtime.
```

### Phase 8 — Multi-day simulation

Goal: model backlog and order ageing without introducing a full multi-period optimizer.

Codex task:

```text
Implement a deterministic day-by-day simulation.

Deferred orders must retain their original creation timestamp.
New orders become eligible according to the dispatch cutoff.
Each delivered order may be delivered only once.
Return daily and cumulative KPIs and final backlog.

Add a hand-verifiable three-day test scenario.
```

## 3. Recommended initial solver settings

```yaml
solver: ortools
solver_time_limit_seconds: 10
first_solution_strategy: PATH_CHEAPEST_ARC
local_search_metaheuristic: GUIDED_LOCAL_SEARCH
random_seed: 42
```

## 4. Recommended development checkpoints

### Checkpoint A

- Domain models complete.
- Validation complete.
- Wellington sample loads.
- No solver yet.

### Checkpoint B

- Offline matrices complete.
- Baseline solver complete.
- ETAs and deferrals tested.

### Checkpoint C

- OR-Tools solver complete.
- Shared solution validator complete.
- Solver comparison available in code.

### Checkpoint D

- Streamlit dispatch UI complete.
- Map and exports working.

### Checkpoint E

- Fleet-size and multi-day simulations complete.
- README includes screenshots and benchmark results.

## 5. Recommended first pull requests

1. `chore: scaffold project and domain models`
2. `feat: add input validation and CSV loaders`
3. `feat: add haversine distance provider`
4. `feat: add greedy insertion baseline`
5. `feat: add OR-Tools CVRP solver`
6. `feat: add solution invariant validator`
7. `feat: add Streamlit dispatch dashboard`
8. `feat: add fleet-size experiments`
9. `feat: add multi-day backlog simulation`

## 6. Documentation maintenance rule

When implementation choices differ from these documents, update the relevant document in the same change. The repository documentation is the source of truth for Codex and reviewers.
