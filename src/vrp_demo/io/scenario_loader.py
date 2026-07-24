from __future__ import annotations

from datetime import date, time
from pathlib import Path
from typing import Any, TextIO

import yaml

from vrp_demo.domain.models import ObjectiveConfig, ScenarioConfig
from vrp_demo.io.csv_loader import InputValidationError


def load_scenario(source: str | Path | TextIO) -> ScenarioConfig:
    try:
        if isinstance(source, Path):
            payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        elif hasattr(source, "read"):
            payload = yaml.safe_load(source.read())
        else:
            payload = yaml.safe_load(source)
        if not isinstance(payload, dict):
            raise ValueError("configuration must be a mapping")
        objective_data = payload.get("objective") or {}
        objective = ObjectiveConfig(**objective_data)
        return ScenarioConfig(
            scenario_id=str(payload["scenario_id"]),
            planning_date=date.fromisoformat(str(payload["planning_date"])),
            dispatch_cutoff=time.fromisoformat(str(payload["dispatch_cutoff"])),
            default_service_minutes=int(payload.get("default_service_minutes", 5)),
            capacity_unit=str(payload.get("capacity_unit", "cartons")),
            distance_provider=str(payload.get("distance_provider", "haversine")),
            solver=str(payload.get("solver", "greedy_insertion")),
            solver_time_limit_seconds=int(payload.get("solver_time_limit_seconds", 10)),
            random_seed=int(payload.get("random_seed", 42)),
            average_speed_kph=float(payload.get("average_speed_kph", 35.0)),
            objective=objective,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InputValidationError(f"Invalid scenario configuration: {exc}") from exc


def scenario_to_dict(config: ScenarioConfig) -> dict[str, Any]:
    return {
        "scenario_id": config.scenario_id,
        "planning_date": config.planning_date.isoformat(),
        "dispatch_cutoff": config.dispatch_cutoff.isoformat(timespec="minutes"),
        "default_service_minutes": config.default_service_minutes,
        "capacity_unit": config.capacity_unit,
        "distance_provider": config.distance_provider,
        "solver": config.solver,
        "solver_time_limit_seconds": config.solver_time_limit_seconds,
        "random_seed": config.random_seed,
        "average_speed_kph": config.average_speed_kph,
        "objective": {
            "deferred_weight": config.objective.deferred_weight,
            "flowtime_weight": config.objective.flowtime_weight,
            "distance_weight": config.objective.distance_weight,
            "age_penalty_per_day": config.objective.age_penalty_per_day,
            "priority_penalty": config.objective.priority_penalty,
        },
    }
