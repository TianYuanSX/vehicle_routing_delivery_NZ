# Acceptance Tests

## 1. Completion rule

Prototype one is accepted only when all critical tests pass and no known defect violates a hard routing constraint.

## 2. Data validation tests

### AT-DATA-001 Valid input

**Given** valid orders, vehicles, one depot, and scenario settings  
**When** the files are loaded  
**Then** validation succeeds and typed domain objects are created.

### AT-DATA-002 Duplicate order IDs

**Given** two rows with the same `order_id`  
**When** validation runs  
**Then** the system reports a fatal duplicate-ID error and does not run the solver.

### AT-DATA-003 Invalid coordinates

**Given** an order latitude outside `[-90, 90]`  
**When** validation runs  
**Then** the system reports a fatal coordinate error.

### AT-DATA-004 Invalid vehicle shift

**Given** a vehicle whose shift end is not later than shift start  
**When** validation runs  
**Then** the system reports a fatal shift error.

### AT-DATA-005 Oversized order

**Given** an order larger than every active vehicle capacity  
**When** validation runs  
**Then** the system shows a warning and the solver returns that order as deferred.

## 3. Solver feasibility tests

### AT-SOLVER-001 Single feasible order

**Given** one vehicle, one feasible order, and sufficient shift time  
**When** either solver runs  
**Then** the route is `depot -> order -> depot`, the order is planned, and ETA is populated.

### AT-SOLVER-002 Capacity exactly reached

**Given** one vehicle with capacity 10 and orders totalling 10  
**When** the solver runs  
**Then** all orders may be assigned and reported utilization is 100%.

### AT-SOLVER-003 Capacity exceeded

**Given** one vehicle with capacity 10 and orders totalling 15  
**When** the solver runs  
**Then** assigned load does not exceed 10 and at least one order is deferred.

### AT-SOLVER-004 Shift-time infeasible

**Given** a route whose travel and service duration cannot fit within the shift  
**When** the solver runs  
**Then** the route is not produced and affected orders are deferred.

### AT-SOLVER-005 Multiple vehicles

**Given** two vehicles and orders requiring both  
**When** the solver runs  
**Then** orders are assigned without duplication and each route is independently feasible.

### AT-SOLVER-006 No active vehicles

**Given** eligible orders and no active vehicles  
**When** the solver runs  
**Then** every order is deferred with `NO_ACTIVE_VEHICLE`.

### AT-SOLVER-007 Every order represented

**Given** any valid instance  
**When** the solver returns  
**Then** the number of `order_results` equals the number of input orders and IDs match exactly.

### AT-SOLVER-008 No duplicate delivery

**Given** any successful solution  
**When** all route stops are inspected  
**Then** no order appears more than once.

### AT-SOLVER-009 Depot boundaries

**Given** any used vehicle route  
**When** the route is inspected  
**Then** it starts and ends at the configured depot.

### AT-SOLVER-010 Objective consistency

**Given** a successful solution  
**When** metrics are recomputed from outputs  
**Then** the recomputed objective components equal the reported values.

## 4. ETA tests

### AT-ETA-001 Travel and service accumulation

**Given** a route with known leg durations and service times  
**When** ETAs are calculated  
**Then** each arrival equals route start plus preceding travel and service durations.

### AT-ETA-002 Departure time

**Given** an order with five minutes of service  
**When** its ETA is 09:30  
**Then** estimated departure is 09:35.

### AT-ETA-003 Route return

**Given** a final delivery stop and a known return-leg duration  
**When** the route is evaluated  
**Then** route end equals final departure plus return travel time.

### AT-ETA-004 Shift compliance

**Given** a planned route  
**When** its route end is inspected  
**Then** it is no later than vehicle shift end.

### AT-ETA-005 Flow time uses original creation

**Given** an order created on the previous day  
**When** it is delivered today  
**Then** flow time begins at the original creation timestamp.

## 5. Multi-day simulation tests

### AT-MULTI-001 Deferred order carried forward

**Given** an order deferred on day one  
**When** day two planning begins  
**Then** the order is included in the day-two backlog with its original creation time.

### AT-MULTI-002 New orders respect cutoff

**Given** one order before and one order after the dispatch cutoff  
**When** the day's eligible set is created  
**Then** only the pre-cutoff order is eligible that day.

### AT-MULTI-003 Backlog clears with added capacity

**Given** an order deferred because of insufficient day-one fleet capacity  
**When** another vehicle is available on day two  
**Then** the order can be planned on day two.

### AT-MULTI-004 No order lost between days

**Given** a three-day simulation  
**When** all daily outputs are reconciled  
**Then** each created order is delivered once or remains in final backlog.

## 6. UI tests

### AT-UI-001 Built-in Wellington scenario

**Given** the application starts without uploaded files  
**When** the Wellington example is selected  
**Then** the scenario loads and can be solved without network access.

### AT-UI-002 CSV upload errors

**Given** an invalid CSV  
**When** it is uploaded  
**Then** the user sees understandable validation errors before solving.

### AT-UI-003 Arbitrary map bounds

**Given** valid coordinates outside Wellington  
**When** results are displayed  
**Then** the map centers and zooms to those coordinates.

### AT-UI-004 Order status visibility

**Given** a mixed solution  
**When** the order table is viewed  
**Then** planned and deferred orders are clearly distinguishable.

### AT-UI-005 Vehicle workload

**Given** a solution with used and unused vehicles  
**When** the workload page is viewed  
**Then** all vehicles are shown with correct utilization and route metrics.

### AT-UI-006 Export

**Given** a completed solve  
**When** the user exports results  
**Then** order, vehicle, and route-leg CSV files match the displayed solution.

### AT-UI-007 Route-line geometry

**Given** a completed solve
**When** the dispatch map uses its default line style
**Then** routes render as offline straight segments without a direction API call.

**And when** road-following lines are selected
**Then** the selected optional direction provider is called for geometry only, the
planned stop sequence is preserved, and an unavailable service visibly falls back
to straight segments.

### AT-UI-008 Basemap theme

**Given** either the input scenario map or a completed dispatch map
**When** the user selects Light or Dark under Map theme
**Then** that map rerenders with the corresponding OpenStreetMap-based basemap style
without changing input data, assignments, route geometry, ETAs, or metrics.

## 7. Fleet-size experiment tests

### AT-FLEET-001 Reproducibility

**Given** the same scenario, seed, solver, and settings  
**When** fleet-size analysis runs twice  
**Then** deterministic solvers produce identical results.

### AT-FLEET-002 Same demand across scenarios

**Given** fleet sizes 1 through N  
**When** the experiment runs  
**Then** every run uses the same orders, matrices, objective weights, and planning time.

### AT-FLEET-003 Metrics returned for each fleet size

**Given** a fleet-size range  
**When** the experiment finishes  
**Then** one complete metric row exists for every tested size.

### AT-FLEET-004 No impossible monotonicity assertion

The application must not assert that distance always decreases or delivery count always strictly increases with fleet size. It should display observed results without unsupported claims.

## 8. Solver comparison tests

### AT-COMP-001 Common input contract

**Given** baseline and OR-Tools solvers  
**When** both are run on the same instance  
**Then** both receive identical validated data and matrices.

### AT-COMP-002 Common output contract

**Given** results from both solvers  
**When** the application displays them  
**Then** no solver-specific UI path is required for core metrics and route display.

### AT-COMP-003 Feasibility before quality

**Given** two solver results  
**When** they are compared  
**Then** infeasible results are never ranked above feasible results solely because of a lower reported objective.

## 9. Performance targets

On a normal developer laptop, using the offline distance provider:

- A 50-order, 10-vehicle example should load and validate interactively.
- The greedy baseline should normally complete in under a few seconds.
- OR-Tools must respect its configured time limit.
- The UI must remain responsive after a solve.

These are demonstration targets and may be revised after measurement.

## 10. Definition of done

Prototype one is done when:

- All critical acceptance tests pass.
- The Wellington example runs offline.
- Both baseline and OR-Tools solvers use the same contracts.
- Every order is planned or deferred.
- All reported routes satisfy capacity and shift constraints.
- ETA and flow-time calculations are tested.
- Fleet-size experiments are reproducible.
- Documentation matches implemented behaviour.
