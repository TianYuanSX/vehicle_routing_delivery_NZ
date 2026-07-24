from __future__ import annotations

from dataclasses import dataclass

from vrp_demo.domain.enums import PlanningStatus, SolverStatus
from vrp_demo.domain.models import (
    Depot,
    DomainValidationError,
    Order,
    RoutingInstance,
    RoutingSolution,
    Vehicle,
)


@dataclass(frozen=True)
class ValidationMessage:
    level: str
    code: str
    message: str


def validate_entities(
    orders: tuple[Order, ...], vehicles: tuple[Vehicle, ...], depots: tuple[Depot, ...]
) -> tuple[ValidationMessage, ...]:
    if len(depots) != 1:
        raise DomainValidationError(f"prototype one requires exactly one depot; got {len(depots)}")
    _unique((order.order_id for order in orders), "order")
    _unique((vehicle.vehicle_id for vehicle in vehicles), "vehicle")
    _unique((depot.depot_id for depot in depots), "depot")
    depot_id = depots[0].depot_id
    missing = sorted({vehicle.depot_id for vehicle in vehicles if vehicle.depot_id != depot_id})
    if missing:
        raise DomainValidationError(f"vehicles reference missing depots: {', '.join(missing)}")
    messages: list[ValidationMessage] = []
    active = [vehicle for vehicle in vehicles if vehicle.active]
    if not active:
        messages.append(ValidationMessage("warning", "NO_ACTIVE_VEHICLE", "No vehicles are active"))
    elif orders:
        maximum = max(vehicle.capacity for vehicle in active)
        oversized = [order.order_id for order in orders if order.size > maximum]
        if oversized:
            messages.append(
                ValidationMessage(
                    "warning",
                    "OVERSIZED_ORDER",
                    f"Orders exceed every active vehicle capacity: {', '.join(oversized)}",
                )
            )
    return tuple(messages)


def _unique(values: object, label: str) -> None:
    materialized = list(values)  # type: ignore[call-overload]
    duplicates = sorted({value for value in materialized if materialized.count(value) > 1})
    if duplicates:
        raise DomainValidationError(f"duplicate {label} IDs: {', '.join(duplicates)}")


def validate_solution(instance: RoutingInstance, solution: RoutingSolution) -> None:
    if solution.solver_status not in {SolverStatus.FEASIBLE, SolverStatus.OPTIMAL}:
        return
    expected = {order.order_id for order in instance.orders}
    actual = [result.order_id for result in solution.order_results]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise DomainValidationError("solution must represent every order exactly once")
    planned = {
        result.order_id
        for result in solution.order_results
        if result.status == PlanningStatus.PLANNED
    }
    routed = [
        stop.order_id
        for route in solution.routes
        for stop in route.stops
        if stop.order_id is not None
    ]
    if set(routed) != planned or len(routed) != len(set(routed)):
        raise DomainValidationError("planned orders and route stops do not reconcile")
    vehicles = {vehicle.vehicle_id: vehicle for vehicle in instance.vehicles}
    for route in solution.routes:
        vehicle = vehicles[route.vehicle_id]
        if route.assigned_load > vehicle.capacity:
            raise DomainValidationError(f"{route.vehicle_id} exceeds capacity")
        if route.route_start_time < vehicle.shift_start or route.route_end_time > vehicle.shift_end:
            raise DomainValidationError(f"{route.vehicle_id} exceeds shift")
        if not route.stops or route.stops[0].location_id != instance.depot.depot_id:
            raise DomainValidationError(f"{route.vehicle_id} does not start at depot")
        if route.stops[-1].location_id != instance.depot.depot_id:
            raise DomainValidationError(f"{route.vehicle_id} does not return to depot")
        if route.route_distance_metres != sum(leg.distance_metres for leg in route.legs):
            raise DomainValidationError(f"{route.vehicle_id} distance does not reconcile")
    metrics = solution.metrics
    if (
        metrics.objective_value
        != metrics.deferred_cost + metrics.flowtime_cost + metrics.distance_cost
    ):
        raise DomainValidationError("objective components do not reconcile")
