from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from vrp_demo.dispatch.planner import build_instance
from vrp_demo.distance.haversine import HaversineDistanceProvider
from vrp_demo.domain.models import Depot, Order, ScenarioConfig, Vehicle


@pytest.fixture
def timezone() -> ZoneInfo:
    return ZoneInfo("Pacific/Auckland")


@pytest.fixture
def depot() -> Depot:
    return Depot("DEPOT", "Test depot", -41.28, 174.78, "Pacific/Auckland")


@pytest.fixture
def scenario() -> ScenarioConfig:
    return ScenarioConfig("test", date(2026, 7, 23), time(8), random_seed=7)


def make_order(
    order_id: str,
    size: int = 5,
    *,
    latitude: float = -41.29,
    longitude: float = 174.79,
    created: datetime | None = None,
    service_seconds: int = 300,
    priority: int = 1,
) -> Order:
    timezone = ZoneInfo("Pacific/Auckland")
    return Order(
        order_id,
        latitude,
        longitude,
        size,
        created or datetime(2026, 7, 22, 12, tzinfo=timezone),
        service_seconds,
        priority,
    )


def make_vehicle(
    vehicle_id: str = "V1",
    capacity: int = 10,
    *,
    shift_start: time = time(8),
    shift_end: time = time(17),
    planning_date: date = date(2026, 7, 23),
) -> Vehicle:
    timezone = ZoneInfo("Pacific/Auckland")
    return Vehicle(
        vehicle_id,
        capacity,
        datetime.combine(planning_date, shift_start, timezone),
        datetime.combine(planning_date, shift_end, timezone),
        "DEPOT",
    )


def make_instance(orders, vehicles, depot, scenario):
    return build_instance(
        tuple(orders),
        tuple(vehicles),
        depot,
        scenario,
        HaversineDistanceProvider(35),
    )
