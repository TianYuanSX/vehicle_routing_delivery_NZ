from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from vrp_demo.distance.base import DistanceProvider
from vrp_demo.domain.models import (
    Depot,
    Order,
    RoutingInstance,
    RoutingSolution,
    ScenarioConfig,
    SolverConfig,
    Vehicle,
)
from vrp_demo.domain.validation import validate_entities, validate_solution
from vrp_demo.solvers.base import RoutingSolver


def build_instance(
    orders: tuple[Order, ...],
    vehicles: tuple[Vehicle, ...],
    depot: Depot,
    scenario: ScenarioConfig,
    distance_provider: DistanceProvider,
) -> RoutingInstance:
    validate_entities(orders, vehicles, (depot,))
    planning_time = datetime.combine(
        scenario.planning_date, scenario.dispatch_cutoff, ZoneInfo(depot.timezone)
    )
    coordinates = [(depot.latitude, depot.longitude)] + [
        (order.latitude, order.longitude) for order in orders
    ]
    matrix = distance_provider.matrix(coordinates)
    return RoutingInstance(
        scenario.scenario_id,
        planning_time,
        depot,
        orders,
        vehicles,
        (depot.depot_id, *(order.order_id for order in orders)),
        matrix.distances_metres,
        matrix.durations_seconds,
        scenario.random_seed,
    )


def solve_dispatch(
    instance: RoutingInstance, solver: RoutingSolver, config: SolverConfig
) -> RoutingSolution:
    solution = solver.solve(instance, config)
    validate_solution(instance, solution)
    return solution
