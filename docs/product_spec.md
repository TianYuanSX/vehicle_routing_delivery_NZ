# Product Specification

## 1. Purpose

Build a demonstrable vehicle-routing and dispatch application for logistics job applications. The application should show both optimization capability and practical dispatch operations.

The first prototype solves a static capacitated vehicle-routing problem with driver working-hour constraints and optional order deferral.

## 2. Product goals

The system should:

- Accept order, vehicle, depot, and scenario data.
- Assign feasible orders to vehicles.
- Generate an ordered route for every used vehicle.
- Estimate arrival and departure times for every planned order.
- Explicitly identify deferred orders.
- Display fleet workload and order status.
- Compare solver performance.
- Simulate the operational effect of changing fleet size.
- Work with a built-in Wellington example and arbitrary valid coordinates.

## 3. Out of scope for prototype one

The first prototype will not include:

- Multiple depots.
- Multiple trips or reloading during a shift.
- Split deliveries.
- Customer delivery time windows.
- Driver breaks or overtime rules.
- Live GPS tracking.
- Live traffic updates.
- Fuel range constraints.
- Electric vehicle charging.
- Stochastic travel times.
- Dynamic order insertion after dispatch.
- Multiple simultaneous capacity dimensions.

These can be introduced after the core architecture is stable.

## 4. Core assumptions

1. There is one depot in each scenario.
2. Every vehicle starts and ends at the depot.
3. Every vehicle performs at most one route per planning day.
4. Every vehicle has one driver.
5. A driver can only operate within the vehicle's configured shift.
6. All orders assigned to a vehicle are loaded before departure.
7. Each order is delivered by one vehicle or deferred.
8. Travel times are deterministic within one solver run.
9. Every order has a non-negative integer size.
10. Every vehicle has a positive integer capacity.
11. Every order has a service duration, either explicit or supplied by a scenario default.
12. Planning is performed at a dispatch cutoff time.
13. Orders created after the cutoff become eligible for the next planning day.
14. Deferred orders retain their original creation timestamp.

## 5. User journeys

### 5.1 Use built-in example

The user selects the Wellington example, chooses a solver, runs optimization, and reviews routes, ETAs, workload, order status, and summary metrics.

The example uses synthetic demand attributes at verified public-facing Wellington
street addresses. Stored coordinates are generated from those addresses so the
example remains reproducible and available offline.

### 5.2 Upload CSV data

The user uploads order, vehicle, and depot CSV files. The system validates them and displays actionable errors before solving.

### 5.3 Enter data manually

The user creates or edits the single depot, orders, and vehicles in editable tables,
then runs the selected solver.

### 5.4 Generate an instance

The user specifies parameters such as order count, vehicle count, capacity range, order-size range, service duration, geographic bounds, and random seed. The application generates a reproducible instance.

### 5.5 Compare fleet sizes

The user selects a minimum and maximum fleet size. The system solves the same scenario repeatedly and compares service and cost metrics.

### 5.6 Simulate multiple days

The user selects a date range. On each day, eligible new orders are combined with backlog orders, solved, and carried forward when deferred.

## 6. Functional requirements

### FR-1 Data ingestion

The application must support:

- Built-in example data.
- CSV upload.
- Manual table input.
- Reproducible generated instances.

### FR-2 Validation

The system must detect and report:

- Missing required columns.
- Duplicate identifiers.
- Invalid coordinates.
- Negative order size.
- Zero or negative vehicle capacity.
- Invalid timestamps.
- Shift end earlier than or equal to shift start.
- Orders whose size exceeds every active vehicle's capacity.

Validation should distinguish fatal errors from warnings.

### FR-3 Solver selection

The application must expose a solver registry. Prototype one should include:

- Greedy cheapest-insertion baseline.
- OR-Tools solver.

Future implementations may include Clarke-Wright savings, genetic algorithms, evolutionary computation, tabu search, simulated annealing, or custom metaheuristics.

### FR-4 Route generation

For each used vehicle, the solution must contain:

- Depot departure.
- Ordered delivery stops.
- Depot return.
- Distance and duration for each leg.
- Arrival and departure timestamps.
- Load and utilization metrics.

### FR-5 Order assignment

Every input order must be returned with one of these daily planning outcomes:

- `PLANNED`
- `DEFERRED`

Simulation may additionally display:

- `PENDING`
- `IN_TRANSIT`
- `DELIVERED`

### FR-6 Estimated arrival time

ETA must include:

- Route departure time.
- Travel time for preceding legs.
- Service duration at preceding stops.
- Optional solver waiting time, if introduced later.

### FR-7 Driver working hours

A planned route must:

- Start no earlier than shift start.
- Finish no later than shift end.

Prototype one does not model breaks or overtime.

### FR-8 Deferred orders

Orders may be deferred when the active fleet cannot feasibly complete them. A deferred order must:

- Remain present in outputs.
- Retain its original creation time.
- Include a deferred reason or reason code.
- Be eligible on the following planning day.

### FR-9 Visualization

The application must show:

- Depot location.
- Order locations.
- A scenario preview that refreshes when valid input data changes.
- One path per vehicle.
- A dispatch-map choice between offline straight segments and optional
  road-following direction-service geometry.
- Stop order.
- Order status.
- ETA and order size on hover or selection.

Map bounds and center must be calculated from scenario coordinates rather than hard-coded for Wellington.

### FR-10 Fleet workload

For each vehicle, display:

- Assigned order count.
- Assigned load.
- Capacity utilization.
- Route distance.
- Route duration.
- Shift utilization.
- Route start and finish time.

### FR-11 Fleet-size simulation

For each tested fleet size, report:

- Delivered orders.
- Deferred orders.
- Total distance.
- Mean flow time.
- Maximum flow time.
- Average capacity utilization.
- Average shift utilization.
- Vehicles used.
- Solver runtime.

### FR-12 Export

The user should be able to export:

- Order results CSV.
- Vehicle results CSV.
- Route-leg results CSV.
- Fleet-size experiment CSV.

## 7. Non-functional requirements

### NFR-1 Reproducibility

All generated instances and experiments must record a random seed. Solver time limits and major search settings must be stored with results.

### NFR-2 Extensibility

New solvers and distance providers should be added without changing UI logic or shared domain models.

### NFR-3 Offline operation

The built-in example and automated tests must work without internet access using the Haversine provider.

### NFR-4 Explainability

The baseline solver should be understandable and traceable. The application should show objective components and reasons for deferral.

### NFR-5 Performance

The initial target is interactive use for approximately:

- Up to 200 orders.
- Up to 30 vehicles.
- A solver time limit configurable between 1 and 60 seconds.

These are demonstration targets, not hard architectural limits.

## 8. Recommended UI pages

1. **Scenario** — data source, uploads, manual input, generation, validation.
2. **Dispatch** — map, routes, headline KPIs, order assignment.
3. **Vehicle workload** — per-vehicle metrics and route stop tables.
4. **Order tracking** — status table and simulated timeline.
5. **Fleet simulation** — scenario comparison charts and table.
6. **Solver comparison** — baseline versus OR-Tools metrics and runtime.

## 9. Open decisions for later versions

- Whether drivers may take multiple trips per day.
- Whether orders have hard delivery deadlines.
- Whether capacity should model weight, volume, pallets, or multiple dimensions.
- Whether fleet-size simulation should include fixed vehicle and labour costs.
- Whether road-network matrices should be locally hosted or externally queried.
- Whether multi-day planning should be optimized jointly rather than simulated sequentially.
