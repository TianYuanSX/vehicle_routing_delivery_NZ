from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from vrp_demo.dispatch.eta import evaluate_route
from vrp_demo.domain.enums import DeferredReason, PlanningStatus, SolverStatus
from vrp_demo.domain.models import (
    OrderResult,
    RoutingInstance,
    RoutingSolution,
    SolutionMetrics,
    SolverConfig,
    VehicleResult,
)


def deferred_penalty(instance: RoutingInstance, order_index: int, config: SolverConfig) -> int:
    order = instance.orders[order_index]
    age_days = max(
        0, int((instance.planning_time - order.order_created_time).total_seconds() // 86400)
    )
    weights = config.objective
    return (
        weights.deferred_weight
        + weights.age_penalty_per_day * age_days
        + weights.priority_penalty * order.priority
    )


def build_solution(
    instance: RoutingInstance,
    config: SolverConfig,
    solver_name: str,
    assignments: Mapping[str, list[int]],
    deferred_reasons: Mapping[int, DeferredReason],
    runtime: float,
    status: SolverStatus = SolverStatus.FEASIBLE,
    metadata: Mapping[str, object] | None = None,
) -> RoutingSolution:
    vehicles_by_id = {vehicle.vehicle_id: vehicle for vehicle in instance.vehicles}
    routes = tuple(
        evaluate_route(instance, vehicles_by_id[vehicle_id], order_indices).route
        for vehicle_id, order_indices in assignments.items()
        if order_indices
    )
    result_by_order: dict[int, OrderResult] = {}
    for route in routes:
        for stop in route.stops:
            if stop.order_id is None:
                continue
            index = next(
                index
                for index, order in enumerate(instance.orders)
                if order.order_id == stop.order_id
            )
            order = instance.orders[index]
            flow_minutes = max(
                0, int((stop.arrival_time - order.order_created_time).total_seconds() // 60)
            )
            result_by_order[index] = OrderResult(
                order.order_id,
                PlanningStatus.PLANNED,
                route.vehicle_id,
                stop.sequence,
                stop.arrival_time,
                stop.departure_time,
                flow_minutes,
                None,
                None,
            )
    reason_messages = {
        DeferredReason.NO_ACTIVE_VEHICLE: "No active vehicle is available",
        DeferredReason.ORDER_EXCEEDS_ALL_VEHICLE_CAPACITIES: (
            "Order exceeds every active vehicle capacity"
        ),
        DeferredReason.SHIFT_TIME_INFEASIBLE: "Order cannot be completed within any driver shift",
        DeferredReason.INSUFFICIENT_TOTAL_CAPACITY: "Available route capacity is insufficient",
        DeferredReason.SOLVER_DROPPED_WITH_PENALTY: "Solver deferred the order with a penalty",
        DeferredReason.SOLVER_TIMEOUT_NO_FEASIBLE_ASSIGNMENT: (
            "Solver timed out without a feasible assignment"
        ),
        DeferredReason.INVALID_ORDER: "Order is invalid",
    }
    for index, reason in deferred_reasons.items():
        order = instance.orders[index]
        result_by_order[index] = OrderResult(
            order.order_id,
            PlanningStatus.DEFERRED,
            None,
            None,
            None,
            None,
            None,
            reason.value,
            reason_messages[reason],
        )
    for index, order in enumerate(instance.orders):
        if index not in result_by_order:
            reason = DeferredReason.SOLVER_DROPPED_WITH_PENALTY
            result_by_order[index] = OrderResult(
                order.order_id,
                PlanningStatus.DEFERRED,
                None,
                None,
                None,
                None,
                None,
                reason.value,
                reason_messages[reason],
            )
    order_results = tuple(result_by_order[index] for index in range(len(instance.orders)))
    route_by_vehicle = {route.vehicle_id: route for route in routes}
    vehicle_results: list[VehicleResult] = []
    used_capacity: list[float] = []
    used_shift: list[float] = []
    operating_cost = 0.0
    costs_supplied = False
    for vehicle in instance.vehicles:
        current_route = route_by_vehicle.get(vehicle.vehicle_id)
        shift_seconds = int((vehicle.shift_end - vehicle.shift_start).total_seconds())
        if current_route is None:
            vehicle_results.append(
                VehicleResult(
                    vehicle.vehicle_id,
                    False,
                    0,
                    0,
                    vehicle.capacity,
                    0.0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    shift_seconds,
                    0.0,
                    None,
                    None,
                )
            )
            continue
        capacity_utilization = current_route.assigned_load / vehicle.capacity
        route_seconds = int(
            (current_route.route_end_time - current_route.route_start_time).total_seconds()
        )
        shift_utilization = route_seconds / shift_seconds
        used_capacity.append(capacity_utilization)
        used_shift.append(shift_utilization)
        if vehicle.cost_per_km or vehicle.fixed_daily_cost:
            costs_supplied = True
        operating_cost += vehicle.fixed_daily_cost + vehicle.cost_per_km * (
            current_route.route_distance_metres / 1000
        )
        vehicle_results.append(
            VehicleResult(
                vehicle.vehicle_id,
                True,
                len(current_route.stops) - 2,
                current_route.assigned_load,
                vehicle.capacity,
                capacity_utilization,
                current_route.route_distance_metres,
                current_route.travel_seconds,
                current_route.service_seconds,
                current_route.waiting_seconds,
                route_seconds,
                shift_seconds,
                shift_utilization,
                current_route.route_start_time,
                current_route.route_end_time,
            )
        )
    flows = [
        result.flow_time_minutes for result in order_results if result.flow_time_minutes is not None
    ]
    deferred_indices = [
        index
        for index, result in enumerate(order_results)
        if result.status == PlanningStatus.DEFERRED
    ]
    deferred_cost = sum(deferred_penalty(instance, index, config) for index in deferred_indices)
    total_flow = sum(flows)
    total_distance = sum(route.route_distance_metres for route in routes)
    flowtime_cost = total_flow * config.objective.flowtime_weight
    distance_cost = total_distance * config.objective.distance_weight
    metrics = SolutionMetrics(
        len(flows),
        len(deferred_indices),
        len(routes),
        total_distance,
        sum(route.travel_seconds for route in routes),
        sum(route.service_seconds for route in routes),
        total_flow,
        total_flow / len(flows) if flows else None,
        max(flows) if flows else None,
        sum(used_capacity) / len(used_capacity) if used_capacity else 0.0,
        sum(used_shift) / len(used_shift) if used_shift else 0.0,
        deferred_cost,
        flowtime_cost,
        distance_cost,
        deferred_cost + flowtime_cost + distance_cost,
        operating_cost if costs_supplied else None,
    )
    configuration = {
        "time_limit_seconds": config.time_limit_seconds,
        "random_seed": config.random_seed,
        "objective": asdict(config.objective),
        "options": dict(config.options),
    }
    return RoutingSolution(
        routes,
        order_results,
        tuple(vehicle_results),
        metrics,
        solver_name,
        status,
        runtime,
        configuration,
        {
            "scenario_id": instance.scenario_id,
            "planning_time": instance.planning_time.isoformat(),
            **(metadata or {}),
        },
    )


def failure_solution(
    instance: RoutingInstance,
    config: SolverConfig,
    solver_name: str,
    runtime: float,
    status: SolverStatus,
    reason: DeferredReason,
    error: str | None = None,
) -> RoutingSolution:
    metadata: dict[str, object] = {}
    if error:
        metadata["error"] = error
    return build_solution(
        instance,
        config,
        solver_name,
        {},
        {index: reason for index in range(len(instance.orders))},
        runtime,
        status,
        metadata,
    )
