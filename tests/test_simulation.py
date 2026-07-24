from datetime import date, datetime, time

import pandas as pd

from tests.conftest import make_instance, make_order, make_vehicle
from vrp_demo.distance.haversine import HaversineDistanceProvider
from vrp_demo.domain.models import ScenarioConfig, SolverConfig
from vrp_demo.simulation.fleet_size import run_fleet_size_analysis
from vrp_demo.simulation.instance_generator import generate_instance_data
from vrp_demo.simulation.multi_day import run_multi_day_simulation
from vrp_demo.solvers.greedy_insertion import GreedyInsertionSolver


def test_generator_is_seeded() -> None:
    first = generate_instance_data(seed=9, number_of_orders=5, number_of_vehicles=2)
    second = generate_instance_data(seed=9, number_of_orders=5, number_of_vehicles=2)
    assert first == second
    assert first[3].random_seed == 9


def test_fleet_size_analysis_is_tidy_and_reproducible(depot, scenario) -> None:
    instance = make_instance(
        [make_order("O1", 6), make_order("O2", 6)],
        [make_vehicle("V1", 6), make_vehicle("V2", 6)],
        depot,
        scenario,
    )
    args = (instance, GreedyInsertionSolver(), SolverConfig(), [1, 2])
    results, frame = run_fleet_size_analysis(*args)
    results_again, frame_again = run_fleet_size_analysis(*args)
    assert len(results) == 2
    assert frame["fleet_size"].tolist() == [1, 2]
    pd.testing.assert_frame_equal(
        frame.drop(columns="solver_runtime_seconds"),
        frame_again.drop(columns="solver_runtime_seconds"),
    )
    assert [row.objective_value for row in results] == [
        row.objective_value for row in results_again
    ]


def test_three_day_backlog_preserves_creation_and_cutoff(depot, timezone) -> None:
    scenario = ScenarioConfig("days", date(2026, 7, 23), time(8), random_seed=3)
    orders = (
        make_order("OLD-A", 5, created=datetime(2026, 7, 23, 7, tzinfo=timezone)),
        make_order("OLD-B", 5, created=datetime(2026, 7, 23, 7, 30, tzinfo=timezone)),
        make_order("LATE", 5, created=datetime(2026, 7, 23, 9, tzinfo=timezone)),
    )

    def vehicles_for_day(day):
        count = 1 if day == date(2026, 7, 23) else 2
        return tuple(make_vehicle(f"V{i}", 5, planning_date=day) for i in range(count))

    result = run_multi_day_simulation(
        orders,
        vehicles_for_day,
        depot,
        scenario,
        GreedyInsertionSolver(),
        SolverConfig(),
        HaversineDistanceProvider(),
        date(2026, 7, 23),
        3,
    )
    assert result.days[0].newly_eligible_orders == 2
    assert result.days[0].deferred_orders == 1
    assert result.days[1].backlog_in == 1
    assert result.days[1].newly_eligible_orders == 1
    assert not result.final_backlog
    assert len(result.delivered_order_ids) == 3
    assert orders[1].order_created_time == datetime(2026, 7, 23, 7, 30, tzinfo=timezone)
