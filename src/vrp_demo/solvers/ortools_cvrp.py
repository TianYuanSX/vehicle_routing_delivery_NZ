from __future__ import annotations

from time import perf_counter

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from vrp_demo.dispatch.result_builder import build_solution, deferred_penalty, failure_solution
from vrp_demo.domain.enums import DeferredReason, SolverStatus
from vrp_demo.domain.models import RoutingInstance, RoutingSolution, SolverConfig

FIRST_STRATEGIES = {
    "PATH_CHEAPEST_ARC": routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    "PARALLEL_CHEAPEST_INSERTION": (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    ),
    "AUTOMATIC": routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
}
LOCAL_SEARCH = {
    "GUIDED_LOCAL_SEARCH": routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    "TABU_SEARCH": routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
    "AUTOMATIC": routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC,
}


class ORToolsCVRPSolver:
    name = "ortools"

    def solve(self, instance: RoutingInstance, config: SolverConfig) -> RoutingSolution:
        started = perf_counter()
        active = [vehicle for vehicle in instance.vehicles if vehicle.active]
        if not active:
            return failure_solution(
                instance,
                config,
                self.name,
                perf_counter() - started,
                SolverStatus.FEASIBLE,
                DeferredReason.NO_ACTIVE_VEHICLE,
            )
        manager = pywrapcp.RoutingIndexManager(
            len(instance.location_ids), len(active), [0] * len(active), [0] * len(active)
        )
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index: int, to_index: int) -> int:
            origin = int(manager.IndexToNode(from_index))
            destination = int(manager.IndexToNode(to_index))
            return (
                instance.distance_matrix_metres[origin][destination]
                * config.objective.distance_weight
            )

        distance_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

        def demand_callback(index: int) -> int:
            node = int(manager.IndexToNode(index))
            return 0 if node == 0 else instance.orders[node - 1].size

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            [vehicle.capacity for vehicle in active],
            True,
            "Capacity",
        )

        def time_callback(from_index: int, to_index: int) -> int:
            origin = int(manager.IndexToNode(from_index))
            destination = int(manager.IndexToNode(to_index))
            service = 0 if origin == 0 else instance.orders[origin - 1].service_seconds
            return service + instance.duration_matrix_seconds[origin][destination]

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        maximum_shift = max(
            int((vehicle.shift_end - instance.planning_time).total_seconds()) for vehicle in active
        )
        horizon = max(1, maximum_shift)
        routing.AddDimension(time_callback_index, 0, horizon, False, "Time")
        time_dimension = routing.GetDimensionOrDie("Time")
        for vehicle_index, vehicle in enumerate(active):
            departure = max(instance.planning_time, vehicle.shift_start)
            start_offset = max(0, int((departure - instance.planning_time).total_seconds()))
            end_offset = int((vehicle.shift_end - instance.planning_time).total_seconds())
            time_dimension.CumulVar(routing.Start(vehicle_index)).SetValue(start_offset)
            time_dimension.CumulVar(routing.End(vehicle_index)).SetRange(start_offset, end_offset)
        for order_index in range(len(instance.orders)):
            routing_index = manager.NodeToIndex(order_index + 1)
            penalty = deferred_penalty(instance, order_index, config)
            routing.AddDisjunction([routing_index], penalty)
            time_dimension.SetCumulVarSoftUpperBound(
                routing_index, 0, config.objective.flowtime_weight
            )
        search = pywrapcp.DefaultRoutingSearchParameters()
        search.first_solution_strategy = FIRST_STRATEGIES.get(
            str(config.options.get("first_solution_strategy", "PATH_CHEAPEST_ARC")),
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        )
        search.local_search_metaheuristic = LOCAL_SEARCH.get(
            str(config.options.get("local_search_metaheuristic", "GUIDED_LOCAL_SEARCH")),
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
        )
        search.time_limit.FromSeconds(config.time_limit_seconds)
        search.log_search = bool(config.options.get("log_search", False))
        assignment = routing.SolveWithParameters(search)
        runtime = perf_counter() - started
        if assignment is None:
            return failure_solution(
                instance,
                config,
                self.name,
                runtime,
                SolverStatus.TIME_LIMIT,
                DeferredReason.SOLVER_TIMEOUT_NO_FEASIBLE_ASSIGNMENT,
                "OR-Tools did not return an assignment",
            )
        assignments: dict[str, list[int]] = {}
        routed: set[int] = set()
        for vehicle_index, vehicle in enumerate(active):
            route: list[int] = []
            index = routing.Start(vehicle_index)
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != 0:
                    route.append(node - 1)
                    routed.add(node - 1)
                index = assignment.Value(routing.NextVar(index))
            assignments[vehicle.vehicle_id] = route
        deferred = {
            index: DeferredReason.SOLVER_DROPPED_WITH_PENALTY
            for index in range(len(instance.orders))
            if index not in routed
        }
        return build_solution(
            instance,
            config,
            self.name,
            assignments,
            deferred,
            runtime,
            SolverStatus.FEASIBLE,
            {
                "ortools_objective_value": assignment.ObjectiveValue(),
                "global_optimality_proven": False,
                "time_epoch": instance.planning_time.isoformat(),
                "time_units": "integer seconds relative to time_epoch",
                "random_seed": config.random_seed,
            },
        )
