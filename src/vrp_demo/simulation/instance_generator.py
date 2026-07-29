from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from vrp_demo.domain.models import Depot, Order, ScenarioConfig, Vehicle


def generate_instance_data(
    *,
    seed: int,
    number_of_orders: int,
    number_of_vehicles: int,
    latitude_bounds: tuple[float, float] = (-41.34, -41.24),
    longitude_bounds: tuple[float, float] = (174.74, 174.83),
    depot_position: tuple[float, float] = (-41.279, 174.780),
    order_size_range: tuple[int, int] = (1, 15),
    vehicle_capacity_range: tuple[int, int] = (25, 50),
    creation_hours_before_cutoff: tuple[int, int] = (1, 36),
    service_minutes_range: tuple[int, int] = (3, 10),
    priority_range: tuple[int, int] = (1, 5),
    planning_date: date = date(2026, 7, 23),
    dispatch_cutoff: time = time(8),
    shift: tuple[time, time] = (time(8), time(17)),
    timezone_name: str = "Pacific/Auckland",
) -> tuple[tuple[Order, ...], tuple[Vehicle, ...], Depot, ScenarioConfig]:
    if number_of_orders < 0 or number_of_vehicles < 0:
        raise ValueError("order and vehicle counts must be non-negative")
    rng = random.Random(seed)
    timezone = ZoneInfo(timezone_name)
    planning_time = datetime.combine(planning_date, dispatch_cutoff, timezone)
    depot = Depot("DEPOT", "Generated depot", *depot_position, timezone_name)
    orders = tuple(
        Order(
            f"ORD-{index + 1:03d}",
            rng.uniform(*latitude_bounds),
            rng.uniform(*longitude_bounds),
            rng.randint(*order_size_range),
            planning_time - timedelta(hours=rng.randint(*creation_hours_before_cutoff)),
            rng.randint(*service_minutes_range) * 60,
            rng.randint(*priority_range),
            address=f"{index + 1} Generated Street",
            customer_name=f"Synthetic customer {index + 1}",
            suburban="Generated area",
            city="Generated city",
        )
        for index in range(number_of_orders)
    )
    vehicles = tuple(
        Vehicle(
            f"VEH-{index + 1:02d}",
            rng.randint(*vehicle_capacity_range),
            datetime.combine(planning_date, shift[0], timezone),
            datetime.combine(planning_date, shift[1], timezone),
            depot.depot_id,
            True,
        )
        for index in range(number_of_vehicles)
    )
    scenario = ScenarioConfig(
        f"generated-{seed}",
        planning_date,
        dispatch_cutoff,
        random_seed=seed,
    )
    return orders, vehicles, depot, scenario
