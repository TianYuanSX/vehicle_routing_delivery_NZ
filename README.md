# Vehicle Routing Solution

A working first prototype of a static, single-depot capacitated vehicle-routing
and dispatch application. It assigns feasible orders to vehicle routes, produces
ETAs, explicitly retains deferred orders, simulates planned tracking, and compares
fleet sizes. The included Wellington dataset is synthetic and works fully offline.

## Features

- Strictly validated order, vehicle, depot, scenario, matrix, and result contracts.
- Deterministic offline Haversine matrices plus an injectable, cached OSRM table
  provider whose tests never use the network.
- A transparent oldest/highest-priority greedy cheapest-insertion baseline.
- An OR-Tools CVRP adapter with capacity/time dimensions, vehicle-specific shifts,
  optional delivery penalties, flow-time pressure, and a configurable time limit.
- Solver-independent routes, ETAs, order results, vehicle workloads, metrics,
  exports, simulations, and UI.
- Built-in Wellington data at geocoded public locations, CSV upload, editable
  manual tables, and seeded instance generation.
- Reactive Streamlit scenario preview and dispatch map with data-derived center/zoom,
  simulated order tracking, vehicle workloads, exports, and reproducible fleet-size
  analysis.
- Day-by-day backlog simulation that preserves creation timestamps.

## Prototype assumptions

There is one depot, one driver and at most one preloaded route per vehicle per day.
Routes start and end at the assigned depot. Deliveries cannot be split, vehicles
cannot reload, and one integer capacity dimension is used. Travel is deterministic
within a run. Driver breaks, customer time windows, live traffic/GPS, multiple
depots, and multiple trips are out of scope. See [ASSUMPTIONS.md](ASSUMPTIONS.md).

## Architecture

The package uses a `src/` layout:

- `domain`: solver-independent inputs, outputs, enums, and invariant validation.
- `io`: CSV/YAML and built-in scenario loading.
- `distance`: the `DistanceProvider` protocol, Haversine, OSRM, and caching.
- `solvers`: the `RoutingSolver` protocol, registry, greedy baseline, and OR-Tools.
- `dispatch`: instance construction, route timing, result construction, and status.
- `simulation`: seeded generation, fleet-size experiments, and multi-day planning.
- `presentation`: map, metric, and export adapters used by Streamlit.

Solver modules do not import UI packages, and presentation code contains no
optimization logic.

## Environment

Python 3.12 is pinned in `.python-version`; dependencies are declared in
`pyproject.toml` and locked in `uv.lock`. Install `uv` using an official method
from the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/),
then run:

```bash
uv python install 3.12
uv sync --locked --all-groups
```

`uv` creates the repository-local `.venv`; no activation is required and project
packages should never be installed globally.

## Run and verify

```bash
uv run streamlit run app.py
uv run pytest
uv run pytest --cov=vrp_demo
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv lock --check
```

The application defaults to the synthetic Wellington scenario and offline
Haversine mode. Select a solver in the sidebar and choose **Solve dispatch**.

## Input modes and schemas

The UI supports:

1. Built-in Wellington example.
2. Three CSV uploads.
3. Editable single-depot, order, and vehicle tables.
4. A deterministic generated instance with an explicit seed.

Minimal order CSV:

```csv
order_id,customer_name,suburban,address,city,latitude,longitude,size,order_created_time,service_minutes,priority
ORD-001,Museum of New Zealand Te Papa Tongarewa,Te Aro,55 Cable Street,Wellington,-41.2903326,174.7819275,12,2026-07-22T14:30:00+12:00,5,2
```

Minimal vehicle CSV:

```csv
vehicle_id,capacity,shift_start,shift_end,depot_id,active
VAN-01,40,08:00,17:00,WLG-DEPOT,true
```

Depot CSV:

```csv
depot_id,name,address,suburban,city,latitude,longitude,timezone
WLG-DEPOT,NZ Post Wellington Super Depot,8 Carmel Terrace,Grenada Village,Wellington,-41.2007115,174.8255637,Pacific/Auckland
```

Timestamps must include an offset. Local vehicle shift times are interpreted on
the selected planning date in the depot's IANA timezone. Additional CSV columns
are retained for compatibility where defined and otherwise safely ignored; missing
required columns, duplicates, and any invalid row stop the complete load.

`suburban`, street `address`, and `city` are separate display fields. Legacy files
that used `address` for the suburb continue to load when `suburban` is absent.
The Wellington example's public address sources and geocoding method are recorded
in [`data/wellington/README.md`](data/wellington/README.md).

## Solver and distance choices

`greedy_insertion` is deterministic and explainable: orders are considered oldest
first, then by descending priority, and placed at the least-cost feasible position.
`ortools` searches a richer neighborhood and may improve quality, but its
`FEASIBLE` status is not a global-optimality claim.

Haversine mode uses direct geographic distance and converts it to time with a
configurable average speed. It is suitable for tests and offline demonstrations.
OSRM distance mode obtains road-network table distance and duration through HTTP
with explicit timeout/error handling.

After solving, **Route line style** controls map geometry independently:

- **Straight lines** is the default offline approximation and calls no direction
  service.
- **Follow roads** reveals the optional direction-service selector. The initial
  implementation uses OSRM's Route service, caches the returned GeoJSON geometry
  for one hour, and falls back visibly to straight lines if OSRM is unavailable.

Road geometry is visualization-only. It preserves the solver's stop order and does
not recalculate assignments, ETAs, reported distance, or objective values. The
public OSRM demonstration endpoint has no production availability guarantee;
production use should select and operate an appropriate hosted or self-hosted
routing service.

The weighted objective approximates the business hierarchy:

1. avoid deferring old or high-priority orders;
2. minimize total delivered-order flow time;
3. minimize total fleet distance.

The UI exposes these weights. Mean flow time is reported but total flow time is
optimized.

## Fleet and multi-day analysis

Open **Fleet analysis** after a dispatch solve, select a fleet-size range, and run
the experiment. Every row uses the same orders, depot, matrices, solver settings,
and seed; only available vehicles change. Distance is shown separately from
operating cost because it is not a complete cost measure.

The reusable `run_multi_day_simulation` API combines eligible new orders with the
backlog at each cutoff, plans one static day at a time, preserves original creation
times, and ensures no order is delivered twice.

## Documentation

- [Product specification](docs/product_spec.md)
- [Data contract](docs/data_contract.md)
- [Solver contract](docs/solver_contract.md)
- [Objective](docs/objective.md)
- [Acceptance tests](docs/acceptance_tests.md)
- [Implementation plan](docs/implementation_plan.md)
- [Implementation report](IMPLEMENTATION_REPORT.md)

## Known limitations and future work

Only OSRM is implemented for optional road geometry; GraphHopper, Valhalla, and
Google Directions remain future `RouteGeometryProvider` adapters. OR-Tools uses a
calibrated weighted objective rather than strict multi-pass lexicographic
optimization, and multi-day simulation is exposed as an application API rather
than its own Streamlit page. Production extensions include multiple depots/trips,
time windows, multiple capacity dimensions, traffic, dynamic dispatch, and
persistent live events.
