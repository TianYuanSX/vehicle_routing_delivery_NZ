from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from vrp_demo.dispatch.planner import build_instance
from vrp_demo.distance.base import DistanceProvider
from vrp_demo.domain.enums import PlanningStatus
from vrp_demo.domain.models import (
    DailySimulationResult,
    Depot,
    MultiDaySimulationResult,
    Order,
    ScenarioConfig,
    SolverConfig,
    Vehicle,
)
from vrp_demo.solvers.base import RoutingSolver

VehicleProvider = Callable[[date], tuple[Vehicle, ...]]


def run_multi_day_simulation(
    orders: tuple[Order, ...],
    vehicles_for_day: VehicleProvider,
    depot: Depot,
    scenario: ScenarioConfig,
    solver: RoutingSolver,
    solver_config: SolverConfig,
    distance_provider: DistanceProvider,
    start_date: date,
    number_of_days: int,
) -> MultiDaySimulationResult:
    delivered: set[str] = set()
    previous_backlog: set[str] = set()
    days: list[DailySimulationResult] = []
    timezone = ZoneInfo(depot.timezone)
    for offset in range(number_of_days):
        planning_date = start_date + timedelta(days=offset)
        cutoff = datetime.combine(planning_date, scenario.dispatch_cutoff, timezone)
        eligible = tuple(
            order
            for order in orders
            if order.order_id not in delivered and order.order_created_time <= cutoff
        )
        eligible_ids = {order.order_id for order in eligible}
        newly_eligible = eligible_ids - previous_backlog
        day_scenario = replace(scenario, planning_date=planning_date)
        day_vehicles = tuple(
            replace(
                vehicle,
                shift_start=datetime.combine(
                    planning_date, vehicle.shift_start.timetz().replace(tzinfo=None), timezone
                ),
                shift_end=datetime.combine(
                    planning_date, vehicle.shift_end.timetz().replace(tzinfo=None), timezone
                ),
            )
            for vehicle in vehicles_for_day(planning_date)
        )
        instance = build_instance(eligible, day_vehicles, depot, day_scenario, distance_provider)
        solution = solver.solve(instance, solver_config)
        delivered_today = {
            result.order_id
            for result in solution.order_results
            if result.status == PlanningStatus.PLANNED
        }
        delivered.update(delivered_today)
        backlog = eligible_ids - delivered_today
        days.append(
            DailySimulationResult(
                planning_date,
                len(eligible),
                len(newly_eligible),
                len(previous_backlog),
                len(delivered_today),
                len(backlog),
                len(delivered),
                solution,
            )
        )
        previous_backlog = backlog
    final_cutoff_date = start_date + timedelta(days=max(0, number_of_days - 1))
    final_cutoff = datetime.combine(final_cutoff_date, scenario.dispatch_cutoff, timezone)
    final_backlog = tuple(
        order
        for order in orders
        if order.order_id not in delivered and order.order_created_time <= final_cutoff
    )
    return MultiDaySimulationResult(
        tuple(days), final_backlog, tuple(sorted(delivered)), scenario.random_seed
    )
