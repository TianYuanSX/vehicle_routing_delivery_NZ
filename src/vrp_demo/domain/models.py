from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time
from math import isfinite
from types import MappingProxyType
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from vrp_demo.domain.enums import OrderStatus, PlanningStatus, SolverStatus


class DomainValidationError(ValueError):
    """A user-correctable domain or input error."""


def _non_empty(value: str, label: str) -> None:
    if not value.strip():
        raise DomainValidationError(f"{label} must be non-empty")


def _coordinates(latitude: float, longitude: float) -> None:
    if not isfinite(latitude) or not -90 <= latitude <= 90:
        raise DomainValidationError(f"latitude must be between -90 and 90, got {latitude}")
    if not isfinite(longitude) or not -180 <= longitude <= 180:
        raise DomainValidationError(f"longitude must be between -180 and 180, got {longitude}")


def _aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError(f"{label} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    latitude: float
    longitude: float
    size: int
    order_created_time: datetime
    service_seconds: int = 300
    priority: int = 1
    status: OrderStatus = OrderStatus.PENDING
    address: str = ""
    customer_name: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        _non_empty(self.order_id, "order_id")
        _coordinates(self.latitude, self.longitude)
        if isinstance(self.size, bool) or self.size <= 0:
            raise DomainValidationError("order size must be a positive integer")
        if self.service_seconds < 0:
            raise DomainValidationError("service duration must be non-negative")
        if not 1 <= self.priority <= 5:
            raise DomainValidationError("priority must be between 1 and 5")
        _aware(self.order_created_time, "order_created_time")


@dataclass(frozen=True, slots=True)
class Vehicle:
    vehicle_id: str
    capacity: int
    shift_start: datetime
    shift_end: datetime
    depot_id: str
    active: bool = True
    driver_id: str | None = None
    cost_per_km: float = 0.0
    fixed_daily_cost: float = 0.0
    speed_factor: float = 1.0

    def __post_init__(self) -> None:
        _non_empty(self.vehicle_id, "vehicle_id")
        _non_empty(self.depot_id, "depot_id")
        if isinstance(self.capacity, bool) or self.capacity <= 0:
            raise DomainValidationError("vehicle capacity must be a positive integer")
        _aware(self.shift_start, "shift_start")
        _aware(self.shift_end, "shift_end")
        if self.shift_end <= self.shift_start:
            raise DomainValidationError("shift_end must be later than shift_start")
        if not isfinite(self.cost_per_km) or self.cost_per_km < 0:
            raise DomainValidationError("cost_per_km must be finite and non-negative")
        if not isfinite(self.fixed_daily_cost) or self.fixed_daily_cost < 0:
            raise DomainValidationError("fixed_daily_cost must be finite and non-negative")
        if not isfinite(self.speed_factor) or self.speed_factor <= 0:
            raise DomainValidationError("speed_factor must be finite and positive")


@dataclass(frozen=True, slots=True)
class Depot:
    depot_id: str
    name: str
    latitude: float
    longitude: float
    timezone: str

    def __post_init__(self) -> None:
        _non_empty(self.depot_id, "depot_id")
        _non_empty(self.name, "depot name")
        _coordinates(self.latitude, self.longitude)
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise DomainValidationError(f"unknown IANA timezone: {self.timezone}") from exc


@dataclass(frozen=True, slots=True)
class ObjectiveConfig:
    deferred_weight: int = 1_000_000
    flowtime_weight: int = 10
    distance_weight: int = 1
    age_penalty_per_day: int = 10_000
    priority_penalty: int = 5_000

    def __post_init__(self) -> None:
        values = (
            self.deferred_weight,
            self.flowtime_weight,
            self.distance_weight,
            self.age_penalty_per_day,
            self.priority_penalty,
        )
        if any(value < 0 for value in values):
            raise DomainValidationError("objective weights must be non-negative")
        if any(value > 10**12 for value in values):
            raise DomainValidationError("objective weights must be at most 10^12")


@dataclass(frozen=True, slots=True)
class SolverConfig:
    time_limit_seconds: int = 10
    random_seed: int = 42
    objective: ObjectiveConfig = field(default_factory=ObjectiveConfig)
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 1 <= self.time_limit_seconds <= 3600:
            raise DomainValidationError("solver time limit must be between 1 and 3600 seconds")
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    scenario_id: str
    planning_date: date
    dispatch_cutoff: time
    default_service_minutes: int = 5
    capacity_unit: str = "cartons"
    distance_provider: str = "haversine"
    solver: str = "greedy_insertion"
    solver_time_limit_seconds: int = 10
    random_seed: int = 42
    average_speed_kph: float = 35.0
    objective: ObjectiveConfig = field(default_factory=ObjectiveConfig)

    def __post_init__(self) -> None:
        _non_empty(self.scenario_id, "scenario_id")
        _non_empty(self.capacity_unit, "capacity_unit")
        if self.default_service_minutes < 0:
            raise DomainValidationError("default_service_minutes must be non-negative")
        if self.dispatch_cutoff.tzinfo is not None:
            raise DomainValidationError("dispatch_cutoff must be a local wall-clock time")
        if self.average_speed_kph <= 0:
            raise DomainValidationError("average_speed_kph must be positive")


@dataclass(frozen=True, slots=True)
class RoutingInstance:
    scenario_id: str
    planning_time: datetime
    depot: Depot
    orders: tuple[Order, ...]
    vehicles: tuple[Vehicle, ...]
    location_ids: tuple[str, ...]
    distance_matrix_metres: tuple[tuple[int, ...], ...]
    duration_matrix_seconds: tuple[tuple[int, ...], ...]
    random_seed: int = 42

    def __post_init__(self) -> None:
        _aware(self.planning_time, "planning_time")
        count = 1 + len(self.orders)
        if len(self.location_ids) != count or self.location_ids[0] != self.depot.depot_id:
            raise DomainValidationError("location_ids must contain depot then every order")
        expected = (self.depot.depot_id, *(order.order_id for order in self.orders))
        if self.location_ids != expected:
            raise DomainValidationError("location_ids order does not match depot and orders")
        for label, matrix in (
            ("distance", self.distance_matrix_metres),
            ("duration", self.duration_matrix_seconds),
        ):
            if len(matrix) != count or any(len(row) != count for row in matrix):
                raise DomainValidationError(f"{label} matrix must be {count} x {count}")
            if any(value < 0 for row in matrix for value in row):
                raise DomainValidationError(f"{label} matrix cannot contain negative values")


@dataclass(frozen=True, slots=True)
class RouteStop:
    location_id: str
    order_id: str | None
    sequence: int
    arrival_time: datetime
    departure_time: datetime
    load_before: int
    load_after: int


@dataclass(frozen=True, slots=True)
class RouteLeg:
    sequence: int
    from_location_id: str
    to_location_id: str
    distance_metres: int
    travel_seconds: int
    arrival_time: datetime
    departure_time: datetime
    load_before: int
    load_after: int


@dataclass(frozen=True, slots=True)
class VehicleRoute:
    vehicle_id: str
    stops: tuple[RouteStop, ...]
    legs: tuple[RouteLeg, ...]
    route_distance_metres: int
    travel_seconds: int
    service_seconds: int
    waiting_seconds: int
    route_start_time: datetime
    route_end_time: datetime
    assigned_load: int


@dataclass(frozen=True, slots=True)
class OrderResult:
    order_id: str
    status: PlanningStatus
    vehicle_id: str | None
    stop_sequence: int | None
    estimated_arrival_time: datetime | None
    estimated_departure_time: datetime | None
    flow_time_minutes: int | None
    deferred_reason_code: str | None
    deferred_reason: str | None
    decision_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VehicleResult:
    vehicle_id: str
    used: bool
    order_count: int
    assigned_load: int
    capacity: int
    capacity_utilization: float
    route_distance_metres: int
    travel_seconds: int
    service_seconds: int
    waiting_seconds: int
    route_duration_seconds: int
    shift_duration_seconds: int
    shift_utilization: float
    departure_time: datetime | None
    return_time: datetime | None


@dataclass(frozen=True, slots=True)
class SolutionMetrics:
    delivered_orders: int
    deferred_orders: int
    vehicles_used: int
    total_distance_metres: int
    total_travel_seconds: int
    total_service_seconds: int
    total_flow_time_minutes: int
    mean_flow_time_minutes: float | None
    maximum_flow_time_minutes: int | None
    average_capacity_utilization: float
    average_shift_utilization: float
    deferred_cost: int
    flowtime_cost: int
    distance_cost: int
    objective_value: int
    operating_cost: float | None = None


@dataclass(frozen=True, slots=True)
class RoutingSolution:
    routes: tuple[VehicleRoute, ...]
    order_results: tuple[OrderResult, ...]
    vehicle_results: tuple[VehicleResult, ...]
    metrics: SolutionMetrics
    solver_name: str
    solver_status: SolverStatus
    solve_time_seconds: float
    configuration: Mapping[str, Any]
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class FleetSizeResult:
    fleet_size: int
    vehicles_used: int
    delivered_orders: int
    deferred_orders: int
    delivery_rate: float
    total_distance_metres: int
    mean_flow_time_minutes: float | None
    maximum_flow_time_minutes: int | None
    average_capacity_utilization: float
    average_shift_utilization: float
    solver_runtime_seconds: float
    objective_value: int
    operating_cost: float | None


@dataclass(frozen=True, slots=True)
class DailySimulationResult:
    planning_date: date
    eligible_orders: int
    newly_eligible_orders: int
    backlog_in: int
    delivered_orders: int
    deferred_orders: int
    cumulative_delivered: int
    solution: RoutingSolution


@dataclass(frozen=True, slots=True)
class MultiDaySimulationResult:
    days: tuple[DailySimulationResult, ...]
    final_backlog: tuple[Order, ...]
    delivered_order_ids: tuple[str, ...]
    random_seed: int
