from pathlib import Path

from vrp_demo.domain.models import Depot, Order, ScenarioConfig, Vehicle
from vrp_demo.io.csv_loader import load_csv_bundle
from vrp_demo.io.scenario_loader import load_scenario


def example_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "wellington"


def load_wellington_example() -> tuple[
    tuple[Order, ...], tuple[Vehicle, ...], Depot, ScenarioConfig
]:
    directory = example_directory()
    scenario = load_scenario(directory / "scenario.yaml")
    orders, vehicles, depot, _ = load_csv_bundle(
        directory / "orders.csv",
        directory / "vehicles.csv",
        directory / "depots.csv",
        scenario.planning_date,
        scenario.default_service_minutes,
    )
    return orders, vehicles, depot, scenario
