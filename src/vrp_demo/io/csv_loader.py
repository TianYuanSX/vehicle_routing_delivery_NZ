from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import date, datetime, time
from io import StringIO
from pathlib import Path
from typing import Any, TextIO
from zoneinfo import ZoneInfo

import pandas as pd

from vrp_demo.domain.enums import OrderStatus
from vrp_demo.domain.models import Depot, DomainValidationError, Order, Vehicle
from vrp_demo.domain.validation import ValidationMessage, validate_entities

ORDER_REQUIRED = {"order_id", "latitude", "longitude", "size", "order_created_time"}
VEHICLE_REQUIRED = {"vehicle_id", "capacity", "shift_start", "shift_end", "depot_id"}
DEPOT_REQUIRED = {"depot_id", "name", "latitude", "longitude", "timezone"}


class InputValidationError(DomainValidationError):
    pass


def _rows(source: str | Path | TextIO, required: set[str], entity: str) -> list[dict[str, str]]:
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8-sig")
    elif hasattr(source, "read"):
        raw = source.read()
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    else:
        text = source
    if not text.strip():
        raise InputValidationError(f"{entity} CSV is empty")
    reader = csv.DictReader(StringIO(text))
    columns = set(reader.fieldnames or ())
    missing = sorted(required - columns)
    if missing:
        raise InputValidationError(f"{entity} CSV is missing columns: {', '.join(missing)}")
    return list(reader)


def _integer(value: str, field: str, row: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"row {row}: {field} must be an integer") from exc
    return parsed


def _float(value: str, field: str, row: int) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"row {row}: {field} must be numeric") from exc
    return parsed


def _boolean(value: str, field: str, row: int) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise InputValidationError(f"row {row}: {field} must be true or false")


def load_orders_csv(
    source: str | Path | TextIO, default_service_minutes: int = 5
) -> tuple[Order, ...]:
    rows = _rows(source, ORDER_REQUIRED, "orders")
    orders: list[Order] = []
    errors: list[str] = []
    for number, row in enumerate(rows, start=2):
        try:
            created = datetime.fromisoformat(row["order_created_time"])
            orders.append(
                Order(
                    order_id=row["order_id"].strip(),
                    latitude=_float(row["latitude"], "latitude", number),
                    longitude=_float(row["longitude"], "longitude", number),
                    size=_integer(row["size"], "size", number),
                    order_created_time=created,
                    service_seconds=60
                    * _integer(
                        row.get("service_minutes") or str(default_service_minutes),
                        "service_minutes",
                        number,
                    ),
                    priority=_integer(row.get("priority") or "1", "priority", number),
                    status=OrderStatus((row.get("status") or "PENDING").strip().upper()),
                    address=(row.get("address") or "").strip(),
                    customer_name=(row.get("customer_name") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )
        except (ValueError, KeyError) as exc:
            errors.append(f"row {number}: {exc}")
    if errors:
        raise InputValidationError("Invalid orders CSV:\n" + "\n".join(errors))
    _duplicates((order.order_id for order in orders), "order")
    return tuple(orders)


def load_depots_csv(source: str | Path | TextIO) -> tuple[Depot, ...]:
    rows = _rows(source, DEPOT_REQUIRED, "depots")
    depots: list[Depot] = []
    errors: list[str] = []
    for number, row in enumerate(rows, start=2):
        try:
            depots.append(
                Depot(
                    row["depot_id"].strip(),
                    row["name"].strip(),
                    _float(row["latitude"], "latitude", number),
                    _float(row["longitude"], "longitude", number),
                    row["timezone"].strip(),
                )
            )
        except (ValueError, KeyError) as exc:
            errors.append(f"row {number}: {exc}")
    if errors:
        raise InputValidationError("Invalid depots CSV:\n" + "\n".join(errors))
    _duplicates((depot.depot_id for depot in depots), "depot")
    return tuple(depots)


def _shift(value: str, planning_date: date, timezone: ZoneInfo, label: str, row: int) -> datetime:
    try:
        if "T" in value or " " in value:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone)
            return parsed
        wall_time = time.fromisoformat(value)
        return datetime.combine(planning_date, wall_time, timezone)
    except ValueError as exc:
        raise InputValidationError(f"row {row}: invalid {label}") from exc


def load_vehicles_csv(
    source: str | Path | TextIO, planning_date: date, depot_timezone: str
) -> tuple[Vehicle, ...]:
    rows = _rows(source, VEHICLE_REQUIRED, "vehicles")
    timezone = ZoneInfo(depot_timezone)
    vehicles: list[Vehicle] = []
    errors: list[str] = []
    for number, row in enumerate(rows, start=2):
        try:
            vehicles.append(
                Vehicle(
                    vehicle_id=row["vehicle_id"].strip(),
                    capacity=_integer(row["capacity"], "capacity", number),
                    shift_start=_shift(
                        row["shift_start"], planning_date, timezone, "shift_start", number
                    ),
                    shift_end=_shift(
                        row["shift_end"], planning_date, timezone, "shift_end", number
                    ),
                    depot_id=row["depot_id"].strip(),
                    active=_boolean(row.get("active") or "true", "active", number),
                    driver_id=(row.get("driver_id") or row["vehicle_id"]).strip(),
                    cost_per_km=_float(row.get("cost_per_km") or "0", "cost_per_km", number),
                    fixed_daily_cost=_float(
                        row.get("fixed_daily_cost") or "0", "fixed_daily_cost", number
                    ),
                    speed_factor=_float(row.get("speed_factor") or "1", "speed_factor", number),
                )
            )
        except (ValueError, KeyError) as exc:
            errors.append(f"row {number}: {exc}")
    if errors:
        raise InputValidationError("Invalid vehicles CSV:\n" + "\n".join(errors))
    _duplicates((vehicle.vehicle_id for vehicle in vehicles), "vehicle")
    return tuple(vehicles)


def _duplicates(values: Iterable[str], entity: str) -> None:
    materialized = list(values)
    duplicates = sorted({value for value in materialized if materialized.count(value) > 1})
    if duplicates:
        raise InputValidationError(f"duplicate {entity} IDs: {', '.join(duplicates)}")


def load_csv_bundle(
    orders_source: str | Path | TextIO,
    vehicles_source: str | Path | TextIO,
    depots_source: str | Path | TextIO,
    planning_date: date,
    default_service_minutes: int = 5,
) -> tuple[tuple[Order, ...], tuple[Vehicle, ...], Depot, tuple[ValidationMessage, ...]]:
    depots = load_depots_csv(depots_source)
    if len(depots) != 1:
        raise InputValidationError(f"prototype one requires exactly one depot; got {len(depots)}")
    orders = load_orders_csv(orders_source, default_service_minutes)
    vehicles = load_vehicles_csv(vehicles_source, planning_date, depots[0].timezone)
    try:
        messages = validate_entities(orders, vehicles, depots)
    except DomainValidationError as exc:
        raise InputValidationError(str(exc)) from exc
    return orders, vehicles, depots[0], messages


def orders_from_dataframe(
    frame: pd.DataFrame, default_service_minutes: int = 5
) -> tuple[Order, ...]:
    return load_orders_csv(frame.to_csv(index=False), default_service_minutes)


def vehicles_from_dataframe(
    frame: pd.DataFrame, planning_date: date, depot_timezone: str
) -> tuple[Vehicle, ...]:
    return load_vehicles_csv(frame.to_csv(index=False), planning_date, depot_timezone)


def dataframe_records(items: Iterable[Any]) -> pd.DataFrame:
    return pd.DataFrame(items)
