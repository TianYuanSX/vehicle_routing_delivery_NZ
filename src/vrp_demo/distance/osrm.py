from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from vrp_demo.distance.base import Coordinate, DistanceMatrix


class HTTPClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], timeout: float) -> Any: ...


class DistanceProviderError(RuntimeError):
    pass


class OSRMDistanceProvider:
    name = "osrm"

    def __init__(
        self,
        base_url: str = "https://router.project-osrm.org",
        timeout_seconds: float = 10.0,
        client: HTTPClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client: HTTPClient = client or httpx.Client()

    def matrix(self, coordinates: Sequence[Coordinate]) -> DistanceMatrix:
        coordinate_path = ";".join(f"{longitude},{latitude}" for latitude, longitude in coordinates)
        try:
            response = self.client.get(
                f"{self.base_url}/table/v1/driving/{coordinate_path}",
                params={"annotations": "distance,duration"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, TimeoutError, ValueError) as exc:
            raise DistanceProviderError(f"OSRM request failed: {exc}") from exc
        if payload.get("code") != "Ok":
            raise DistanceProviderError(f"OSRM returned status {payload.get('code', 'unknown')}")
        try:
            raw_distances = payload["distances"]
            raw_durations = payload["durations"]
            size = len(coordinates)
            if len(raw_distances) != size or len(raw_durations) != size:
                raise ValueError("matrix row count mismatch")
            distances = tuple(tuple(round(float(value)) for value in row) for row in raw_distances)
            durations = tuple(tuple(round(float(value)) for value in row) for row in raw_durations)
            if any(len(row) != size for row in distances + durations):
                raise ValueError("matrix column count mismatch")
        except (KeyError, TypeError, ValueError) as exc:
            raise DistanceProviderError(f"OSRM response is malformed: {exc}") from exc
        return DistanceMatrix(
            distances,
            durations,
            self.name,
            False,
            {"base_url": self.base_url, "geometry": "road-network matrix"},
        )
