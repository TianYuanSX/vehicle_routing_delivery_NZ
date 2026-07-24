from datetime import date

import pytest

from vrp_demo.io.csv_loader import (
    InputValidationError,
    load_csv_bundle,
    load_orders_csv,
)

DEPOTS = """depot_id,name,latitude,longitude,timezone
DEPOT,Depot,-41.28,174.78,Pacific/Auckland
"""
VEHICLES = """vehicle_id,capacity,shift_start,shift_end,depot_id
V1,10,08:00,17:00,DEPOT
"""
ORDERS = """order_id,latitude,longitude,size,order_created_time
O1,-41.29,174.79,5,2026-07-22T12:00:00+12:00
"""


def test_valid_csv_bundle_loads() -> None:
    orders, vehicles, depot, messages = load_csv_bundle(ORDERS, VEHICLES, DEPOTS, date(2026, 7, 23))
    assert (len(orders), len(vehicles), depot.depot_id, messages) == (1, 1, "DEPOT", ())


def test_extra_columns_are_accepted_for_compatibility() -> None:
    orders = load_orders_csv(
        ORDERS.replace("order_created_time", "order_created_time,extra").replace(
            "+12:00", "+12:00,ignored"
        )
    )
    assert orders[0].order_id == "O1"


@pytest.mark.parametrize(
    "csv_text,message",
    [
        ("", "empty"),
        ("order_id,size\nO1,1\n", "missing columns"),
        (ORDERS + "O1,-41.3,174.8,2,2026-07-22T12:00:00+12:00\n", "duplicate"),
        (ORDERS.replace("-41.29", "100"), "latitude"),
        (ORDERS.replace("+12:00", ""), "timezone-aware"),
        (ORDERS.replace(",5,", ",not-a-number,"), "integer"),
    ],
)
def test_invalid_orders_are_all_rejected(csv_text: str, message: str) -> None:
    with pytest.raises(InputValidationError, match=message):
        load_orders_csv(csv_text)


def test_mixed_valid_and_invalid_rows_reports_row() -> None:
    mixed = ORDERS + "O2,-41.3,174.8,bad,2026-07-22T12:00:00+12:00\n"
    with pytest.raises(InputValidationError, match="row 3"):
        load_orders_csv(mixed)


def test_missing_depot_reference_is_fatal() -> None:
    with pytest.raises(InputValidationError, match="missing depots"):
        load_csv_bundle(
            ORDERS,
            VEHICLES.replace(",DEPOT", ",MISSING"),
            DEPOTS,
            date(2026, 7, 23),
        )
