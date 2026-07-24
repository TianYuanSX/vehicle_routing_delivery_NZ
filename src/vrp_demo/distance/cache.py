from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from vrp_demo.distance.base import Coordinate, DistanceMatrix, DistanceProvider


class CachedDistanceProvider:
    def __init__(self, provider: DistanceProvider, cache_directory: Path) -> None:
        self.provider = provider
        self.cache_directory = cache_directory
        self.name = f"cached-{provider.name}"

    def matrix(self, coordinates: Sequence[Coordinate]) -> DistanceMatrix:
        settings = {
            "provider": self.provider.name,
            "coordinates": [[latitude, longitude] for latitude, longitude in coordinates],
            "average_speed_kph": getattr(self.provider, "average_speed_kph", None),
            "base_url": getattr(self.provider, "base_url", None),
        }
        serialized = json.dumps(settings, sort_keys=True, separators=(",", ":"))
        key = hashlib.sha256(serialized.encode()).hexdigest()
        path = self.cache_directory / f"{key}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload["settings"] == settings:
                return DistanceMatrix(
                    tuple(tuple(row) for row in payload["distances_metres"]),
                    tuple(tuple(row) for row in payload["durations_seconds"]),
                    payload["provider_name"],
                    payload["approximate"],
                    payload["metadata"] | {"cache_hit": True},
                )
        matrix = self.provider.matrix(coordinates)
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "settings": settings,
            "distances_metres": matrix.distances_metres,
            "durations_seconds": matrix.durations_seconds,
            "provider_name": matrix.provider_name,
            "approximate": matrix.approximate,
            "metadata": matrix.metadata,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return matrix
