from __future__ import annotations

from time import perf_counter

from vrp_demo.dispatch.eta import evaluate_route
from vrp_demo.dispatch.result_builder import build_solution
from vrp_demo.domain.enums import DeferredReason
from vrp_demo.domain.models import RoutingInstance, RoutingSolution, SolverConfig


class GreedyInsertionSolver:
    """Deterministic oldest/highest-priority cheapest feasible insertion."""

    name = "greedy_insertion"

    def solve(self, instance: RoutingInstance, config: SolverConfig) -> RoutingSolution:
        started = perf_counter()
        active = [vehicle for vehicle in instance.vehicles if vehicle.active]
        assignments: dict[str, list[int]] = {vehicle.vehicle_id: [] for vehicle in active}
        deferred: dict[int, DeferredReason] = {}
        if not active:
            deferred = {
                index: DeferredReason.NO_ACTIVE_VEHICLE for index in range(len(instance.orders))
            }
            return build_solution(
                instance,
                config,
                self.name,
                assignments,
                deferred,
                perf_counter() - started,
            )
        order_indices = sorted(
            range(len(instance.orders)),
            key=lambda index: (
                instance.orders[index].order_created_time,
                -instance.orders[index].priority,
                instance.orders[index].order_id,
            ),
        )
        maximum_capacity = max(vehicle.capacity for vehicle in active)
        for order_index in order_indices:
            order = instance.orders[order_index]
            if order.size > maximum_capacity:
                deferred[order_index] = DeferredReason.ORDER_EXCEEDS_ALL_VEHICLE_CAPACITIES
                continue
            best: tuple[int, str, list[int]] | None = None
            any_capacity = False
            for vehicle in active:
                current = assignments[vehicle.vehicle_id]
                if (
                    sum(instance.orders[index].size for index in current) + order.size
                    > vehicle.capacity
                ):
                    continue
                any_capacity = True
                current_evaluation = evaluate_route(instance, vehicle, current)
                for position in range(len(current) + 1):
                    candidate = [*current[:position], order_index, *current[position:]]
                    evaluation = evaluate_route(instance, vehicle, candidate)
                    if not evaluation.feasible:
                        continue
                    incremental_distance = (
                        evaluation.route.route_distance_metres
                        - current_evaluation.route.route_distance_metres
                    )
                    arrival = next(
                        stop.arrival_time
                        for stop in evaluation.route.stops
                        if stop.order_id == order.order_id
                    )
                    flow_minutes = max(
                        0, int((arrival - order.order_created_time).total_seconds() // 60)
                    )
                    score = (
                        incremental_distance * config.objective.distance_weight
                        + flow_minutes * config.objective.flowtime_weight
                    )
                    choice = (score, vehicle.vehicle_id, candidate)
                    if best is None or (choice[0], choice[1], position) < (
                        best[0],
                        best[1],
                        best[2].index(order_index),
                    ):
                        best = choice
            if best is None:
                deferred[order_index] = (
                    DeferredReason.SHIFT_TIME_INFEASIBLE
                    if any_capacity
                    else DeferredReason.INSUFFICIENT_TOTAL_CAPACITY
                )
            else:
                assignments[best[1]] = best[2]
        return build_solution(
            instance,
            config,
            self.name,
            assignments,
            deferred,
            perf_counter() - started,
            metadata={
                "algorithm": "oldest/highest-priority cheapest feasible insertion",
                "global_optimality_proven": False,
            },
        )
