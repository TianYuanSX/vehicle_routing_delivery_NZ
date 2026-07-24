from __future__ import annotations

import pandas as pd

from vrp_demo.domain.models import FleetSizeResult, RoutingInstance, SolverConfig
from vrp_demo.solvers.base import RoutingSolver


def run_fleet_size_analysis(
    instance: RoutingInstance,
    solver: RoutingSolver,
    config: SolverConfig,
    fleet_sizes: range | list[int],
) -> tuple[tuple[FleetSizeResult, ...], pd.DataFrame]:
    results: list[FleetSizeResult] = []
    for fleet_size in fleet_sizes:
        if fleet_size < 0 or fleet_size > len(instance.vehicles):
            raise ValueError("fleet size must be between zero and available vehicle count")
        scenario_instance = RoutingInstance(
            instance.scenario_id,
            instance.planning_time,
            instance.depot,
            instance.orders,
            instance.vehicles[:fleet_size],
            instance.location_ids,
            instance.distance_matrix_metres,
            instance.duration_matrix_seconds,
            instance.random_seed,
        )
        solution = solver.solve(scenario_instance, config)
        metrics = solution.metrics
        row = FleetSizeResult(
            fleet_size,
            metrics.vehicles_used,
            metrics.delivered_orders,
            metrics.deferred_orders,
            metrics.delivered_orders / len(instance.orders) if instance.orders else 1.0,
            metrics.total_distance_metres,
            metrics.mean_flow_time_minutes,
            metrics.maximum_flow_time_minutes,
            metrics.average_capacity_utilization,
            metrics.average_shift_utilization,
            solution.solve_time_seconds,
            metrics.objective_value,
            metrics.operating_cost,
        )
        results.append(row)
    frame = pd.DataFrame(
        [
            {
                "fleet_size": row.fleet_size,
                "vehicles_used": row.vehicles_used,
                "delivered_orders": row.delivered_orders,
                "deferred_orders": row.deferred_orders,
                "delivery_rate": row.delivery_rate,
                "total_distance_metres": row.total_distance_metres,
                "mean_flow_time_minutes": row.mean_flow_time_minutes,
                "maximum_flow_time_minutes": row.maximum_flow_time_minutes,
                "average_capacity_utilization": row.average_capacity_utilization,
                "average_shift_utilization": row.average_shift_utilization,
                "solver_runtime_seconds": row.solver_runtime_seconds,
                "objective_value": row.objective_value,
                "operating_cost": row.operating_cost,
            }
            for row in results
        ]
    )
    return tuple(results), frame
