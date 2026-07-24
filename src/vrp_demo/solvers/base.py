from typing import Protocol

from vrp_demo.domain.models import RoutingInstance, RoutingSolution, SolverConfig


class RoutingSolver(Protocol):
    name: str

    def solve(self, instance: RoutingInstance, config: SolverConfig) -> RoutingSolution: ...
