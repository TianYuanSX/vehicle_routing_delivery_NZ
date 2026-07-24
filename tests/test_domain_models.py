from datetime import datetime

import pytest

from tests.conftest import make_order, make_vehicle
from vrp_demo.domain.models import Depot, DomainValidationError, ObjectiveConfig


def test_order_requires_timezone() -> None:
    with pytest.raises(DomainValidationError, match="timezone-aware"):
        make_order("O1", created=datetime(2026, 7, 22, 12))


@pytest.mark.parametrize("latitude,longitude", [(91, 0), (0, 181)])
def test_coordinates_are_validated(latitude: float, longitude: float) -> None:
    with pytest.raises(DomainValidationError):
        make_order("O1", latitude=latitude, longitude=longitude)


def test_vehicle_shift_and_capacity_are_validated() -> None:
    with pytest.raises(DomainValidationError, match="capacity"):
        make_vehicle(capacity=0)


def test_depot_timezone_is_validated() -> None:
    with pytest.raises(DomainValidationError, match="IANA"):
        Depot("D", "Depot", 0, 0, "Not/AZone")


def test_objective_weights_are_bounded() -> None:
    with pytest.raises(DomainValidationError):
        ObjectiveConfig(deferred_weight=10**13)
