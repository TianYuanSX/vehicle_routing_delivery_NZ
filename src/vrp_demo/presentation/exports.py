from __future__ import annotations

import json
from dataclasses import asdict

import pandas as pd

from vrp_demo.domain.models import RoutingSolution


def order_results_frame(solution: RoutingSolution) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": result.order_id,
                "planning_status": result.status.value,
                "vehicle_id": result.vehicle_id,
                "stop_sequence": result.stop_sequence,
                "estimated_arrival_time": result.estimated_arrival_time,
                "estimated_departure_time": result.estimated_departure_time,
                "flow_time_minutes": result.flow_time_minutes,
                "deferred_reason_code": result.deferred_reason_code,
                "deferred_reason": result.deferred_reason,
                "solver_name": solution.solver_name,
            }
            for result in solution.order_results
        ]
    )


def vehicle_results_frame(solution: RoutingSolution) -> pd.DataFrame:
    return pd.DataFrame([asdict(result) for result in solution.vehicle_results])


def route_legs_frame(solution: RoutingSolution) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"vehicle_id": route.vehicle_id, **asdict(leg)}
            for route in solution.routes
            for leg in route.legs
        ]
    )


def solution_json(solution: RoutingSolution) -> str:
    payload = {
        "solver_name": solution.solver_name,
        "solver_status": solution.solver_status.value,
        "solve_time_seconds": solution.solve_time_seconds,
        "configuration": dict(solution.configuration),
        "metadata": dict(solution.metadata),
        "metrics": asdict(solution.metrics),
        "orders": order_results_frame(solution).to_dict(orient="records"),
        "vehicles": vehicle_results_frame(solution).to_dict(orient="records"),
        "route_legs": route_legs_frame(solution).to_dict(orient="records"),
    }
    return json.dumps(payload, default=str, indent=2)
