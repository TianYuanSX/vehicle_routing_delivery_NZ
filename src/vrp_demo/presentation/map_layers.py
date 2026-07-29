from __future__ import annotations

import math

import pydeck as pdk

from vrp_demo.domain.enums import PlanningStatus
from vrp_demo.domain.models import Depot, Order, RoutingInstance, RoutingSolution

COLORS = [
    [31, 119, 180],
    [255, 127, 14],
    [44, 160, 44],
    [214, 39, 40],
    [148, 103, 189],
    [140, 86, 75],
]


def map_view(coordinates: list[tuple[float, float]]) -> tuple[float, float, float]:
    if not coordinates:
        return 0.0, 0.0, 1.0
    latitudes = [point[0] for point in coordinates]
    longitudes = [point[1] for point in coordinates]
    center_latitude = (min(latitudes) + max(latitudes)) / 2
    center_longitude = (min(longitudes) + max(longitudes)) / 2
    span = max(max(latitudes) - min(latitudes), max(longitudes) - min(longitudes), 0.001)
    zoom = max(1.0, min(15.0, math.log2(180 / span) - 1.0))
    return center_latitude, center_longitude, zoom


def scenario_deck(depot: Depot, orders: tuple[Order, ...]) -> pdk.Deck:
    """Build a reactive input preview without requiring a solved route."""
    points = [
        {
            "location_id": depot.depot_id,
            "position": [depot.longitude, depot.latitude],
            "status": "DEPOT",
            "color": [20, 20, 20],
            "radius": 180,
            "customer_name": depot.name,
            "address": getattr(depot, "address", ""),
            "suburban": getattr(depot, "suburban", ""),
            "city": getattr(depot, "city", ""),
            "details": "Depot",
        },
        *[
            {
                "location_id": order.order_id,
                "position": [order.longitude, order.latitude],
                "status": "ORDER",
                "color": [31, 119, 180],
                "radius": 120,
                "customer_name": getattr(order, "customer_name", "") or order.order_id,
                "address": getattr(order, "address", ""),
                "suburban": getattr(order, "suburban", ""),
                "city": getattr(order, "city", ""),
                "details": f"Order size: {order.size}",
            }
            for order in orders
        ],
    ]
    latitude, longitude, zoom = map_view(
        [(depot.latitude, depot.longitude)]
        + [(order.latitude, order.longitude) for order in orders]
    )
    return pdk.Deck(
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                points,
                get_position="position",
                get_fill_color="color",
                get_radius="radius",
                pickable=True,
            )
        ],
        initial_view_state=pdk.ViewState(
            latitude=latitude, longitude=longitude, zoom=zoom, pitch=0
        ),
        tooltip={
            "html": (
                "<b>{customer_name}</b><br>{location_id} · {status}<br>"
                "{address}<br>{suburban}, {city}<br>{details}"
            )
        },
    )


def dispatch_deck(instance: RoutingInstance, solution: RoutingSolution) -> pdk.Deck:
    coordinates = {
        instance.depot.depot_id: [instance.depot.longitude, instance.depot.latitude],
        **{order.order_id: [order.longitude, order.latitude] for order in instance.orders},
    }
    result_by_id = {result.order_id: result for result in solution.order_results}
    points = [
        {
            "location_id": instance.depot.depot_id,
            "position": coordinates[instance.depot.depot_id],
            "status": "DEPOT",
            "color": [20, 20, 20],
            "radius": 180,
            "customer_name": instance.depot.name,
            "address": instance.depot.address,
            "suburban": instance.depot.suburban,
            "city": instance.depot.city,
            "details": "Depot",
        }
    ]
    for order in instance.orders:
        result = result_by_id[order.order_id]
        points.append(
            {
                "location_id": order.order_id,
                "position": coordinates[order.order_id],
                "status": result.status.value,
                "color": (
                    [200, 30, 30] if result.status == PlanningStatus.DEFERRED else [30, 150, 80]
                ),
                "radius": 120,
                "customer_name": order.customer_name,
                "address": order.address,
                "suburban": order.suburban,
                "city": order.city,
                "details": (
                    f"size={order.size}; vehicle={result.vehicle_id or '-'}; "
                    f"stop={result.stop_sequence or '-'}; "
                    f"ETA={result.estimated_arrival_time or '-'}"
                ),
            }
        )
    paths = []
    for route_index, route in enumerate(solution.routes):
        paths.append(
            {
                "vehicle_id": route.vehicle_id,
                "path": [coordinates[stop.location_id] for stop in route.stops],
                "color": COLORS[route_index % len(COLORS)],
            }
        )
    all_coordinates = [(point[1], point[0]) for point in coordinates.values()]
    latitude, longitude, zoom = map_view(all_coordinates)
    layers = [
        pdk.Layer(
            "PathLayer",
            paths,
            get_path="path",
            get_color="color",
            width_scale=5,
            width_min_pixels=3,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            points,
            get_position="position",
            get_fill_color="color",
            get_radius="radius",
            pickable=True,
        ),
    ]
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=latitude, longitude=longitude, zoom=zoom, pitch=0
        ),
        tooltip={
            "html": (
                "<b>{customer_name}</b><br>{location_id} · {status}<br>"
                "{address}<br>{suburban}, {city}<br>{details}"
            )
        },
    )
