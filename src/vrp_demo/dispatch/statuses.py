from datetime import datetime

from vrp_demo.domain.enums import OrderStatus, PlanningStatus
from vrp_demo.domain.models import OrderResult, RoutingSolution


def simulated_status(result: OrderResult, simulation_time: datetime) -> OrderStatus:
    if result.status == PlanningStatus.DEFERRED:
        return OrderStatus.DEFERRED
    if result.estimated_arrival_time is None or result.estimated_departure_time is None:
        return OrderStatus.PENDING
    if simulation_time < result.estimated_arrival_time:
        return OrderStatus.PLANNED
    if simulation_time < result.estimated_departure_time:
        return OrderStatus.IN_TRANSIT
    return OrderStatus.DELIVERED


def solution_statuses(
    solution: RoutingSolution, simulation_time: datetime
) -> dict[str, OrderStatus]:
    return {
        result.order_id: simulated_status(result, simulation_time)
        for result in solution.order_results
    }
