from datetime import datetime, time

import pytest

from tests.conftest import make_instance, make_order, make_vehicle
from vrp_demo.domain.enums import DeferredReason, PlanningStatus, SolverStatus
from vrp_demo.domain.models import ObjectiveConfig, SolverConfig
from vrp_demo.domain.validation import validate_solution
from vrp_demo.solvers.registry import get_solver


@pytest.mark.parametrize("solver_name", ["greedy_insertion", "ortools"])
def test_single_order_route_and_eta(solver_name, depot, scenario) -> None:
    order = make_order("O1")
    vehicle = make_vehicle(capacity=5)
    instance = make_instance([order], [vehicle], depot, scenario)
    solution = get_solver(solver_name).solve(instance, SolverConfig(time_limit_seconds=1))
    validate_solution(instance, solution)
    assert solution.solver_status == SolverStatus.FEASIBLE
    assert solution.metrics.delivered_orders == 1
    assert [stop.location_id for stop in solution.routes[0].stops] == ["DEPOT", "O1", "DEPOT"]
    assert solution.order_results[0].estimated_departure_time == (
        solution.order_results[0].estimated_arrival_time.replace()
        + (solution.routes[0].stops[1].departure_time - solution.routes[0].stops[1].arrival_time)
    )


@pytest.mark.parametrize("solver_name", ["greedy_insertion", "ortools"])
def test_capacity_mixed_and_all_orders_represented(solver_name, depot, scenario) -> None:
    orders = [make_order("O1", 6), make_order("O2", 4), make_order("O3", 5)]
    instance = make_instance(orders, [make_vehicle(capacity=10)], depot, scenario)
    solution = get_solver(solver_name).solve(instance, SolverConfig(time_limit_seconds=1))
    validate_solution(instance, solution)
    assert len(solution.order_results) == 3
    assert solution.metrics.delivered_orders == 2
    assert solution.routes[0].assigned_load <= 10


@pytest.mark.parametrize("solver_name", ["greedy_insertion", "ortools"])
def test_oversized_and_no_active_vehicle_reasons(solver_name, depot, scenario) -> None:
    instance = make_instance([make_order("BIG", 20)], [make_vehicle(capacity=10)], depot, scenario)
    solution = get_solver(solver_name).solve(instance, SolverConfig(time_limit_seconds=1))
    assert solution.order_results[0].status == PlanningStatus.DEFERRED
    if solver_name == "greedy_insertion":
        assert (
            solution.order_results[0].deferred_reason_code
            == DeferredReason.ORDER_EXCEEDS_ALL_VEHICLE_CAPACITIES
        )
    inactive = make_vehicle()
    object.__setattr__(inactive, "active", False)
    empty = make_instance([make_order("O1")], [inactive], depot, scenario)
    result = get_solver(solver_name).solve(empty, SolverConfig(time_limit_seconds=1))
    assert result.order_results[0].deferred_reason_code == DeferredReason.NO_ACTIVE_VEHICLE


@pytest.mark.parametrize("solver_name", ["greedy_insertion", "ortools"])
def test_shift_and_depot_return_feasibility(solver_name, depot, scenario) -> None:
    vehicle = make_vehicle(shift_start=time(8), shift_end=time(8, 1))
    instance = make_instance(
        [make_order("O1", latitude=-42, longitude=175, service_seconds=300)],
        [vehicle],
        depot,
        scenario,
    )
    solution = get_solver(solver_name).solve(instance, SolverConfig(time_limit_seconds=1))
    assert solution.metrics.deferred_orders == 1
    assert not solution.routes


@pytest.mark.parametrize("solver_name", ["greedy_insertion", "ortools"])
def test_old_and_priority_orders_receive_preference(solver_name, depot, scenario, timezone) -> None:
    old = make_order("OLD", 10, created=datetime(2026, 7, 20, 8, tzinfo=timezone), priority=1)
    new = make_order("NEW", 10, created=datetime(2026, 7, 23, 7, tzinfo=timezone), priority=5)
    instance = make_instance([new, old], [make_vehicle(capacity=10)], depot, scenario)
    config = SolverConfig(
        1,
        objective=ObjectiveConfig(
            deferred_weight=1_000_000,
            age_penalty_per_day=100_000,
            priority_penalty=1,
        ),
    )
    solution = get_solver(solver_name).solve(instance, config)
    planned = {
        result.order_id
        for result in solution.order_results
        if result.status == PlanningStatus.PLANNED
    }
    assert planned == {"OLD"}

    low = make_order("LOW", 10, priority=1)
    high = make_order("HIGH", 10, priority=5)
    priority_instance = make_instance([low, high], [make_vehicle(capacity=10)], depot, scenario)
    priority_solution = get_solver(solver_name).solve(
        priority_instance,
        SolverConfig(1, objective=ObjectiveConfig(priority_penalty=100_000)),
    )
    priority_planned = {
        result.order_id
        for result in priority_solution.order_results
        if result.status == PlanningStatus.PLANNED
    }
    assert priority_planned == {"HIGH"}


def test_deterministic_greedy_output(depot, scenario) -> None:
    instance = make_instance(
        [make_order("O1"), make_order("O2", longitude=174.8)],
        [make_vehicle()],
        depot,
        scenario,
    )
    solver = get_solver("greedy_insertion")
    first = solver.solve(instance, SolverConfig())
    second = solver.solve(instance, SolverConfig())
    assert first.routes == second.routes
    assert first.metrics.objective_value == second.metrics.objective_value
