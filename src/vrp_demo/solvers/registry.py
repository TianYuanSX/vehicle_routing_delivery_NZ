from collections.abc import Callable

from vrp_demo.solvers.base import RoutingSolver
from vrp_demo.solvers.greedy_insertion import GreedyInsertionSolver
from vrp_demo.solvers.ortools_cvrp import ORToolsCVRPSolver

SOLVERS: dict[str, Callable[[], RoutingSolver]] = {
    "greedy_insertion": GreedyInsertionSolver,
    "ortools": ORToolsCVRPSolver,
}


def get_solver(name: str) -> RoutingSolver:
    try:
        return SOLVERS[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown solver {name!r}; choose one of {', '.join(SOLVERS)}") from exc
