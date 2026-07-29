from datetime import datetime, timedelta
from types import SimpleNamespace

from tests.conftest import make_instance, make_order, make_vehicle
from vrp_demo.dispatch.statuses import solution_statuses
from vrp_demo.domain.enums import OrderStatus
from vrp_demo.domain.models import SolverConfig
from vrp_demo.presentation.exports import (
    order_results_frame,
    route_legs_frame,
    solution_json,
    vehicle_results_frame,
)
from vrp_demo.presentation.manual_input import depot_to_manual_frame, orders_to_manual_frame
from vrp_demo.presentation.map_layers import map_view, scenario_deck
from vrp_demo.solvers.greedy_insertion import GreedyInsertionSolver


def test_map_view_uses_arbitrary_coordinates() -> None:
    latitude, longitude, zoom = map_view([(51.5, -0.1), (51.6, 0.1)])
    assert latitude == 51.55
    assert longitude == 0
    assert 1 <= zoom <= 15


def test_scenario_map_contains_depot_and_orders(depot) -> None:
    deck = scenario_deck(depot, (make_order("O1"), make_order("O2")))
    payload = deck.to_json()

    assert '"location_id": "DEPOT"' in payload
    assert '"location_id": "O1"' in payload
    assert '"location_id": "O2"' in payload
    assert payload.count('"status": "ORDER"') == 2
    assert '"status": "DEPOT"' in payload


def test_manual_input_accepts_order_from_before_structured_addresses(timezone) -> None:
    legacy_order = SimpleNamespace(
        order_id="LEGACY-1",
        latitude=-41.29,
        longitude=174.78,
        size=4,
        order_created_time=datetime(2026, 7, 22, 12, tzinfo=timezone),
        service_seconds=300,
        priority=1,
        customer_name="Legacy customer",
        address="Te Aro",
    )

    row = orders_to_manual_frame([legacy_order]).iloc[0]

    assert row["suburban"] == "Te Aro"
    assert row["address"] == ""
    assert row["city"] == ""


def test_depot_is_converted_to_manual_input(depot) -> None:
    row = depot_to_manual_frame(depot).iloc[0]

    assert row["depot_id"] == "DEPOT"
    assert row["name"] == "Test depot"
    assert row["latitude"] == -41.28
    assert row["longitude"] == 174.78
    assert row["timezone"] == "Pacific/Auckland"


def test_exports_reconcile_and_statuses_advance(depot, scenario) -> None:
    instance = make_instance([make_order("O1")], [make_vehicle()], depot, scenario)
    solution = GreedyInsertionSolver().solve(instance, SolverConfig())
    order_frame = order_results_frame(solution)
    vehicle_frame = vehicle_results_frame(solution)
    leg_frame = route_legs_frame(solution)
    assert len(order_frame) == 1
    assert len(vehicle_frame) == 1
    assert leg_frame["distance_metres"].sum() == solution.metrics.total_distance_metres
    assert '"solver_name": "greedy_insertion"' in solution_json(solution)
    arrival = solution.order_results[0].estimated_arrival_time
    departure = solution.order_results[0].estimated_departure_time
    assert arrival is not None and departure is not None
    assert solution_statuses(solution, arrival - timedelta(seconds=1))["O1"] == OrderStatus.PLANNED
    assert solution_statuses(solution, arrival)["O1"] == OrderStatus.IN_TRANSIT
    assert solution_statuses(solution, departure)["O1"] == OrderStatus.DELIVERED
