from __future__ import annotations

from collections.abc import Sequence
from math import asin, cos, radians, sin, sqrt

from vrp_demo.distance.base import Coordinate, DistanceMatrix

EARTH_RADIUS_METRES = 6_371_008.8


def haversine_metres(origin: Coordinate, destination: Coordinate) -> int:
    lat1, lon1 = map(radians, origin)
    lat2, lon2 = map(radians, destination)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return round(2 * EARTH_RADIUS_METRES * asin(sqrt(a)))


class HaversineDistanceProvider:
    name = "haversine"

    def __init__(self, average_speed_kph: float = 35.0) -> None:
        if average_speed_kph <= 0:
            raise ValueError("average_speed_kph must be positive")
        self.average_speed_kph = average_speed_kph

    def matrix(self, coordinates: Sequence[Coordinate]) -> DistanceMatrix:
        speed_metres_per_second = self.average_speed_kph / 3.6
        distances = tuple(
            tuple(
                0 if i == j else haversine_metres(origin, destination)
                for j, destination in enumerate(coordinates)
            )
            for i, origin in enumerate(coordinates)
        )
        durations = tuple(
            tuple(
                0 if i == j else max(1, round(distance / speed_metres_per_second))
                for j, distance in enumerate(row)
            )
            for i, row in enumerate(distances)
        )
        return DistanceMatrix(
            distances,
            durations,
            self.name,
            True,
            {"average_speed_kph": self.average_speed_kph, "geometry": "straight-line"},
        )
