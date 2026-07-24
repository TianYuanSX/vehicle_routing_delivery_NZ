from dataclasses import asdict

import pandas as pd

from vrp_demo.domain.models import RoutingSolution


def headline_metrics(solution: RoutingSolution) -> dict[str, object]:
    metrics = asdict(solution.metrics)
    return {
        "solver": solution.solver_name,
        "status": solution.solver_status.value,
        "runtime_seconds": solution.solve_time_seconds,
        **metrics,
    }


def comparison_frame(solutions: list[RoutingSolution]) -> pd.DataFrame:
    return pd.DataFrame([headline_metrics(solution) for solution in solutions])
