from pathlib import Path

import httpx
import pytest

from vrp_demo.distance.cache import CachedDistanceProvider
from vrp_demo.distance.haversine import HaversineDistanceProvider, haversine_metres
from vrp_demo.distance.osrm import DistanceProviderError, OSRMDistanceProvider


def test_haversine_is_deterministic_and_symmetric() -> None:
    coordinates = [(-41.28, 174.78), (-41.29, 174.79)]
    matrix = HaversineDistanceProvider(36).matrix(coordinates)
    assert matrix.distances_metres[0][1] == matrix.distances_metres[1][0]
    assert matrix.durations_seconds[0][1] == round(matrix.distances_metres[0][1] / 10)
    assert haversine_metres(coordinates[0], coordinates[0]) == 0


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def get(self, url, *, params, timeout):
        self.calls += 1
        return FakeResponse(self.payload)


def test_osrm_uses_injected_client_without_network() -> None:
    client = FakeClient(
        {"code": "Ok", "distances": [[0, 123.4], [124, 0]], "durations": [[0, 12], [13, 0]]}
    )
    matrix = OSRMDistanceProvider(client=client).matrix([(0, 0), (1, 1)])
    assert matrix.distances_metres == ((0, 123), (124, 0))
    assert client.calls == 1


def test_osrm_malformed_response_is_clear() -> None:
    with pytest.raises(DistanceProviderError, match="malformed"):
        OSRMDistanceProvider(client=FakeClient({"code": "Ok"})).matrix([(0, 0)])


def test_osrm_http_failure_is_wrapped() -> None:
    class BrokenClient:
        def get(self, url, *, params, timeout):
            raise httpx.TimeoutException("late")

    with pytest.raises(DistanceProviderError, match="failed"):
        OSRMDistanceProvider(client=BrokenClient()).matrix([(0, 0)])


def test_cache_prevents_duplicate_provider_call(tmp_path: Path) -> None:
    client = FakeClient({"code": "Ok", "distances": [[0]], "durations": [[0]]})
    provider = CachedDistanceProvider(OSRMDistanceProvider(client=client), tmp_path)
    provider.matrix([(0, 0)])
    second = provider.matrix([(0, 0)])
    assert client.calls == 1
    assert second.metadata["cache_hit"] is True
