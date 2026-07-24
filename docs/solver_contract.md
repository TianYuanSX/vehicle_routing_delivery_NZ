# Solver Contract

## 1. Purpose

This document defines the interface between routing solvers and the rest of the application. It allows OR-Tools, heuristic baselines, and future evolutionary solvers to use the same input and output models.

## 2. Design principles

- Solvers operate on validated domain objects.
- Solvers do not know about Streamlit or presentation code.
- Solvers do not read CSV files directly.
- Solvers do not call mapping widgets.
- Distance and travel-time matrices are supplied through the routing instance.
- Every solver returns all orders, including deferred orders.
- Every solver records status and runtime.

## 3. Required domain types

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol


class PlanningStatus(str, Enum):
    PLANNED = "PLANNED"
    DEFERRED = "DEFERRED"


class SolverStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIME_LIMIT = "TIME_LIMIT"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Order:
    order_id: str
    latitude: float
    longitude: float
    size: int
    order_created_time: datetime
    service_seconds: int
    priority: int = 1


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    capacity: int
    shift_start: datetime
    shift_end: datetime
    depot_id: str
    active: bool = True


@dataclass(frozen=True)
class Depot:
    depot_id: str
    latitude: float
    longitude: float
    timezone: str
```

## 4. Routing instance

```python
@dataclass(frozen=True)
class RoutingInstance:
    scenario_id: str
    planning_time: datetime
    depot: Depot
    orders: tuple[Order, ...]
    vehicles: tuple[Vehicle, ...]
    location_ids: tuple[str, ...]
    distance_matrix_metres: tuple[tuple[int, ...], ...]
    duration_matrix_seconds: tuple[tuple[int, ...], ...]
```

The matrix index order must match `location_ids`. The depot should normally be index 0.

## 5. Solver configuration

```python
@dataclass(frozen=True)
class ObjectiveWeights:
    deferred_weight: int
    flowtime_weight: int
    distance_weight: int
    age_penalty_per_day: int
    priority_penalty: int


@dataclass(frozen=True)
class SolverConfig:
    time_limit_seconds: int
    random_seed: int
    objective: ObjectiveWeights
    options: dict[str, object]
```

`options` stores solver-specific settings without leaking them into the common interface.

## 6. Solver interface

```python
class RoutingSolver(Protocol):
    name: str

    def solve(
        self,
        instance: RoutingInstance,
        config: SolverConfig,
    ) -> "RoutingSolution":
        ...
```

The method must not mutate the input instance.

## 7. Shared result types

```python
@dataclass(frozen=True)
class RouteStop:
    location_id: str
    order_id: str | None
    sequence: int
    arrival_time: datetime
    departure_time: datetime
    load_before: int
    load_after: int


@dataclass(frozen=True)
class RouteLeg:
    sequence: int
    from_location_id: str
    to_location_id: str
    distance_metres: int
    travel_seconds: int
    arrival_time: datetime
    departure_time: datetime
    load_before: int
    load_after: int


@dataclass(frozen=True)
class VehicleRoute:
    vehicle_id: str
    stops: tuple[RouteStop, ...]
    legs: tuple[RouteLeg, ...]
    route_distance_metres: int
    travel_seconds: int
    service_seconds: int
    route_start_time: datetime
    route_end_time: datetime
    assigned_load: int


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    status: PlanningStatus
    vehicle_id: str | None
    stop_sequence: int | None
    estimated_arrival_time: datetime | None
    estimated_departure_time: datetime | None
    flow_time_minutes: int | None
    deferred_reason_code: str | None
    deferred_reason: str | None


@dataclass(frozen=True)
class SolutionMetrics:
    delivered_orders: int
    deferred_orders: int
    vehicles_used: int
    total_distance_metres: int
    total_travel_seconds: int
    total_service_seconds: int
    total_flow_time_minutes: int
    mean_flow_time_minutes: float | None
    maximum_flow_time_minutes: int | None
    deferred_cost: int
    flowtime_cost: int
    distance_cost: int
    objective_value: int


@dataclass(frozen=True)
class RoutingSolution:
    routes: tuple[VehicleRoute, ...]
    order_results: tuple[OrderResult, ...]
    metrics: SolutionMetrics
    solver_name: str
    solver_status: SolverStatus
    solve_time_seconds: float
    metadata: dict[str, object]
```

## 8. Required solver invariants

A successful `OPTIMAL` or `FEASIBLE` solution must satisfy:

1. Every input order appears exactly once in `order_results`.
2. Every `PLANNED` order appears exactly once across route stops.
3. Every `DEFERRED` order appears in no route.
4. Each route belongs to one active vehicle.
5. Each route starts at the scenario depot.
6. Each route ends at the scenario depot.
7. Assigned load does not exceed vehicle capacity.
8. Route departure is not earlier than shift start.
9. Route return is not later than shift end.
10. Arrival and departure timestamps are non-decreasing.
11. Departure from an order equals arrival plus service duration.
12. Route and solution totals match the sum of leg and order values.

## 9. Baseline solver behaviour

The recommended baseline is greedy cheapest insertion:

1. Sort orders by oldest creation time first, then highest priority, then order ID.
2. For each order, test every insertion position in every active vehicle route.
3. Reject an insertion when capacity or shift feasibility is violated.
4. Score feasible insertions by incremental objective cost.
5. Select the lowest-cost insertion.
6. Defer the order when no feasible insertion exists.
7. Optionally apply deterministic 2-opt improvement to each route.

The baseline must be deterministic for a fixed instance and seed.

## 10. OR-Tools solver behaviour

The OR-Tools implementation should use:

- Arc cost based on distance.
- Capacity dimension based on order size.
- Time dimension based on travel plus service duration.
- Per-vehicle shift bounds.
- Disjunction penalties for optional delivery.
- Soft time costs or equivalent objective terms for flow time.
- Configurable first-solution strategy.
- Configurable local-search metaheuristic.
- Explicit time limit.

The OR-Tools adapter must convert solver-specific variables into the shared result types.

## 11. Deferred reason assignment

A solver should use the most specific reason available. Recommended precedence:

1. Invalid order.
2. Order exceeds every active vehicle capacity.
3. No active vehicle.
4. Shift-time infeasible under all vehicles.
5. Insufficient combined capacity.
6. Solver dropped with penalty.
7. Solver timeout without feasible assignment.

Some reasons require post-solution diagnosis and may be approximate. The application should label inferred reasons as such in metadata when appropriate.

## 12. Failure behaviour

If a solver raises an internal exception:

- Catch it at the solver boundary.
- Return `SolverStatus.ERROR` when a safe result can be constructed.
- Include an error summary in metadata.
- Do not fabricate routes.
- Keep all orders in the output as deferred with an appropriate error reason when possible.

## 13. Solver comparison

Solvers must be compared using identical:

- Orders.
- Vehicles.
- Distance and duration matrices.
- Objective weights.
- Planning time.
- Time limit where applicable.
- Random seed where applicable.

The comparison table should include feasibility, objective components, delivered orders, total distance, flow-time metrics, and runtime.
