from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, Protocol

import httpx

from vrp_demo.distance.base import Coordinate


class HTTPClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], timeout: float) -> Any: ...


class RouteGeometryError(RuntimeError):
    """A direction service could not provide a usable road geometry."""


@dataclass(frozen=True, slots=True)
class RouteGeometry:
    coordinates: tuple[Coordinate, ...]
    provider_name: str
    metadata: dict[str, object]


class RouteGeometryProvider(Protocol):
    name: str

    def route(self, coordinates: Sequence[Coordinate]) -> RouteGeometry: ...


class OSRMRouteGeometryProvider:
    name = "osrm"

    def __init__(
        self,
        base_url: str = "https://router.project-osrm.org",
        timeout_seconds: float = 15.0,
        client: HTTPClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client: HTTPClient = client or httpx.Client()

    def route(self, coordinates: Sequence[Coordinate]) -> RouteGeometry:
        if len(coordinates) < 2:
            raise RouteGeometryError("a road route requires at least two coordinates")
        coordinate_path = ";".join(f"{longitude},{latitude}" for latitude, longitude in coordinates)
        try:
            response = self.client.get(
                f"{self.base_url}/route/v1/driving/{coordinate_path}",
                params={
                    "alternatives": "false",
                    "steps": "false",
                    "geometries": "geojson",
                    "overview": "full",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, TimeoutError, ValueError) as exc:
            raise RouteGeometryError(f"OSRM direction request failed: {exc}") from exc
        if payload.get("code") != "Ok":
            raise RouteGeometryError(
                f"OSRM returned direction status {payload.get('code', 'unknown')}"
            )
        try:
            raw_coordinates = payload["routes"][0]["geometry"]["coordinates"]
            parsed = tuple((float(point[1]), float(point[0])) for point in raw_coordinates)
            if len(parsed) < 2:
                raise ValueError("route contains fewer than two points")
            if any(
                not isfinite(latitude)
                or not isfinite(longitude)
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
                for latitude, longitude in parsed
            ):
                raise ValueError("route contains invalid coordinates")
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise RouteGeometryError(f"OSRM direction response is malformed: {exc}") from exc
        return RouteGeometry(
            parsed,
            self.name,
            {
                "base_url": self.base_url,
                "geometry": "road-following GeoJSON",
                "waypoint_count": len(coordinates),
            },
        )
