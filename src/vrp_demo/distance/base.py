from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

Coordinate = tuple[float, float]


@dataclass(frozen=True, slots=True)
class DistanceMatrix:
    distances_metres: tuple[tuple[int, ...], ...]
    durations_seconds: tuple[tuple[int, ...], ...]
    provider_name: str
    approximate: bool
    metadata: dict[str, object]


class DistanceProvider(Protocol):
    name: str

    def matrix(self, coordinates: Sequence[Coordinate]) -> DistanceMatrix: ...
