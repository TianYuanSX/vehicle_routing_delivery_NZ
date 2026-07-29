from pathlib import Path

import httpx
import pytest

from vrp_demo.distance.cache import CachedDistanceProvider
from vrp_demo.distance.haversine import HaversineDistanceProvider, haversine_metres
from vrp_demo.distance.osrm import DistanceProviderError, OSRMDistanceProvider
from vrp_demo.distance.route_geometry import (
    OSRMRouteGeometryProvider,
    RouteGeometryError,
)


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
        self.last_url = ""
        self.last_params = {}

    def get(self, url, *, params, timeout):
        self.calls += 1
        self.last_url = url
        self.last_params = params
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


def test_osrm_route_geometry_uses_geojson_without_network() -> None:
    client = FakeClient(
        {
            "code": "Ok",
            "routes": [
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[174.78, -41.28], [174.79, -41.29]],
                    }
                }
            ],
        }
    )
    geometry = OSRMRouteGeometryProvider(client=client).route([(-41.28, 174.78), (-41.29, 174.79)])

    assert geometry.coordinates == ((-41.28, 174.78), (-41.29, 174.79))
    assert geometry.provider_name == "osrm"
    assert client.calls == 1
    assert "/route/v1/driving/" in client.last_url
    assert client.last_params["geometries"] == "geojson"
    assert client.last_params["overview"] == "full"


@pytest.mark.parametrize(
    "payload",
    [
        {"code": "NoRoute"},
        {"code": "Ok", "routes": []},
        {"code": "Ok", "routes": [{"geometry": {"coordinates": []}}]},
    ],
)
def test_osrm_route_geometry_errors_are_clear(payload) -> None:
    with pytest.raises(RouteGeometryError):
        OSRMRouteGeometryProvider(client=FakeClient(payload)).route(
            [(-41.28, 174.78), (-41.29, 174.79)]
        )


def test_cache_prevents_duplicate_provider_call(tmp_path: Path) -> None:
    client = FakeClient({"code": "Ok", "distances": [[0]], "durations": [[0]]})
    provider = CachedDistanceProvider(OSRMDistanceProvider(client=client), tmp_path)
    provider.matrix([(0, 0)])
    second = provider.matrix([(0, 0)])
    assert client.calls == 1
    assert second.metadata["cache_hit"] is True
