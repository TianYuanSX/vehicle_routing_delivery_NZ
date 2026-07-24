from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from vrp_demo.domain.models import RouteLeg, RouteStop, RoutingInstance, Vehicle, VehicleRoute


@dataclass(frozen=True)
class RouteEvaluation:
    route: VehicleRoute
    feasible: bool


def evaluate_route(
    instance: RoutingInstance, vehicle: Vehicle, order_indices: list[int]
) -> RouteEvaluation:
    departure = max(instance.planning_time, vehicle.shift_start)
    current_time = departure
    assigned_load = sum(instance.orders[index].size for index in order_indices)
    load = assigned_load
    depot_id = instance.depot.depot_id
    stops: list[RouteStop] = [RouteStop(depot_id, None, 0, departure, departure, load, load)]
    legs: list[RouteLeg] = []
    previous_location_index = 0
    previous_id = depot_id
    travel_seconds = 0
    service_seconds = 0
    for sequence, order_index in enumerate(order_indices, start=1):
        location_index = order_index + 1
        order = instance.orders[order_index]
        travel = instance.duration_matrix_seconds[previous_location_index][location_index]
        distance = instance.distance_matrix_metres[previous_location_index][location_index]
        arrival = current_time + timedelta(seconds=travel)
        departure_at_stop = arrival + timedelta(seconds=order.service_seconds)
        after = load - order.size
        legs.append(
            RouteLeg(
                sequence,
                previous_id,
                order.order_id,
                distance,
                travel,
                arrival,
                departure_at_stop,
                load,
                after,
            )
        )
        stops.append(
            RouteStop(
                order.order_id,
                order.order_id,
                sequence,
                arrival,
                departure_at_stop,
                load,
                after,
            )
        )
        current_time = departure_at_stop
        previous_location_index = location_index
        previous_id = order.order_id
        load = after
        travel_seconds += travel
        service_seconds += order.service_seconds
    return_travel = instance.duration_matrix_seconds[previous_location_index][0]
    return_distance = instance.distance_matrix_metres[previous_location_index][0]
    return_time = current_time + timedelta(seconds=return_travel)
    legs.append(
        RouteLeg(
            len(order_indices) + 1,
            previous_id,
            depot_id,
            return_distance,
            return_travel,
            return_time,
            return_time,
            load,
            load,
        )
    )
    stops.append(
        RouteStop(
            depot_id,
            None,
            len(order_indices) + 1,
            return_time,
            return_time,
            load,
            load,
        )
    )
    travel_seconds += return_travel
    route = VehicleRoute(
        vehicle.vehicle_id,
        tuple(stops),
        tuple(legs),
        sum(leg.distance_metres for leg in legs),
        travel_seconds,
        service_seconds,
        0,
        departure,
        return_time,
        assigned_load,
    )
    return RouteEvaluation(
        route,
        assigned_load <= vehicle.capacity
        and departure >= vehicle.shift_start
        and return_time <= vehicle.shift_end,
    )
