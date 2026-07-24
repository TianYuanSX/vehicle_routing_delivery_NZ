from __future__ import annotations

import logging
from dataclasses import asdict, replace
from datetime import date, time
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from vrp_demo.dispatch.planner import build_instance, solve_dispatch
from vrp_demo.dispatch.statuses import solution_statuses
from vrp_demo.distance.haversine import HaversineDistanceProvider
from vrp_demo.distance.osrm import DistanceProviderError, OSRMDistanceProvider
from vrp_demo.domain.models import ObjectiveConfig, ScenarioConfig, SolverConfig
from vrp_demo.io.csv_loader import (
    InputValidationError,
    load_csv_bundle,
    orders_from_dataframe,
    vehicles_from_dataframe,
)
from vrp_demo.io.example_data import load_wellington_example
from vrp_demo.presentation.exports import (
    order_results_frame,
    route_legs_frame,
    solution_json,
    vehicle_results_frame,
)
from vrp_demo.presentation.map_layers import dispatch_deck
from vrp_demo.simulation.fleet_size import run_fleet_size_analysis
from vrp_demo.simulation.instance_generator import generate_instance_data
from vrp_demo.solvers.registry import SOLVERS, get_solver

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Vehicle Routing Demo", layout="wide")
st.title("Vehicle Routing and Dispatch Prototype")
st.caption("Static planning and simulated tracking — not live GPS tracking.")

with st.sidebar:
    st.header("Scenario")
    input_mode = st.selectbox(
        "Input mode",
        ["Built-in Wellington", "CSV upload", "Manual tables", "Generated instance"],
    )
    solver_name = st.selectbox("Solver", list(SOLVERS), index=1)
    distance_name = st.selectbox("Distance provider", ["haversine", "osrm"])
    average_speed = st.slider("Haversine average speed (km/h)", 10, 100, 35)
    time_limit = st.slider("Solver time limit (seconds)", 1, 60, 5)
    planning_date = st.date_input("Planning date", date(2026, 7, 23))
    cutoff = st.time_input("Dispatch cutoff", time(8))
    st.subheader("Objective weights")
    deferred_weight = st.number_input("Deferral", 0, 2_000_000_000, 1_000_000)
    flow_weight = st.number_input("Flow time", 0, 1_000_000, 10)
    distance_weight = st.number_input("Distance", 0, 1_000_000, 1)
    age_weight = st.number_input("Age/day", 0, 1_000_000, 10_000)
    priority_weight = st.number_input("Priority", 0, 1_000_000, 5_000)

orders = vehicles = depot = scenario = None
try:
    if input_mode == "Built-in Wellington":
        orders, vehicles, depot, scenario = load_wellington_example()
        scenario = replace(scenario, planning_date=planning_date, dispatch_cutoff=cutoff)
    elif input_mode == "CSV upload":
        order_file = st.file_uploader("Orders CSV", type="csv")
        vehicle_file = st.file_uploader("Vehicles CSV", type="csv")
        depot_file = st.file_uploader("Depot CSV", type="csv")
        if order_file and vehicle_file and depot_file:
            orders, vehicles, depot, _ = load_csv_bundle(
                order_file, vehicle_file, depot_file, planning_date
            )
            scenario = ScenarioConfig("uploaded", planning_date, cutoff)
    elif input_mode == "Generated instance":
        order_count = st.sidebar.slider("Generated orders", 1, 200, 20)
        vehicle_count = st.sidebar.slider("Generated vehicles", 1, 30, 5)
        seed = st.sidebar.number_input("Random seed", 0, 2**31 - 1, 42)
        orders, vehicles, depot, scenario = generate_instance_data(
            seed=int(seed),
            number_of_orders=order_count,
            number_of_vehicles=vehicle_count,
            planning_date=planning_date,
            dispatch_cutoff=cutoff,
        )
    else:
        sample_orders, sample_vehicles, depot, scenario = load_wellington_example()
        order_frame = pd.DataFrame(
            [
                {
                    "order_id": order.order_id,
                    "latitude": order.latitude,
                    "longitude": order.longitude,
                    "size": order.size,
                    "order_created_time": order.order_created_time.isoformat(),
                    "service_minutes": order.service_seconds // 60,
                    "priority": order.priority,
                }
                for order in sample_orders
            ]
        )
        vehicle_frame = pd.DataFrame(
            [
                {
                    "vehicle_id": vehicle.vehicle_id,
                    "capacity": vehicle.capacity,
                    "shift_start": vehicle.shift_start.strftime("%H:%M"),
                    "shift_end": vehicle.shift_end.strftime("%H:%M"),
                    "depot_id": vehicle.depot_id,
                    "active": vehicle.active,
                }
                for vehicle in sample_vehicles
            ]
        )
        edited_orders = st.data_editor(order_frame, num_rows="dynamic")
        edited_vehicles = st.data_editor(vehicle_frame, num_rows="dynamic")
        orders = orders_from_dataframe(edited_orders)
        vehicles = vehicles_from_dataframe(edited_vehicles, planning_date, depot.timezone)
        scenario = replace(scenario, planning_date=planning_date, dispatch_cutoff=cutoff)
except (InputValidationError, ValueError) as exc:
    st.error(str(exc))

if orders is None or vehicles is None or depot is None or scenario is None:
    st.info("Provide all required input files to continue.")
    st.stop()

scenario = replace(
    scenario,
    solver=solver_name,
    distance_provider=distance_name,
    solver_time_limit_seconds=time_limit,
    average_speed_kph=float(average_speed),
    objective=ObjectiveConfig(
        int(deferred_weight),
        int(flow_weight),
        int(distance_weight),
        int(age_weight),
        int(priority_weight),
    ),
)
solver_config = SolverConfig(
    time_limit,
    scenario.random_seed,
    scenario.objective,
    {
        "first_solution_strategy": "PATH_CHEAPEST_ARC",
        "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
    },
)
distance_provider = (
    HaversineDistanceProvider(average_speed)
    if distance_name == "haversine"
    else OSRMDistanceProvider()
)

if st.button("Solve dispatch", type="primary"):
    try:
        try:
            instance = build_instance(orders, vehicles, depot, scenario, distance_provider)
        except DistanceProviderError:
            if distance_name != "osrm":
                raise
            logger.warning("OSRM unavailable; using deterministic Haversine fallback")
            st.warning("OSRM is unavailable. This run uses the offline Haversine fallback.")
            scenario = replace(scenario, distance_provider="haversine")
            instance = build_instance(
                orders, vehicles, depot, scenario, HaversineDistanceProvider(average_speed)
            )
        solution = solve_dispatch(instance, get_solver(solver_name), solver_config)
        st.session_state["instance"] = instance
        st.session_state["solution"] = solution
        st.session_state["scenario"] = scenario
    except Exception as exc:
        logger.exception("Dispatch solve failed")
        st.error(f"Unable to solve scenario: {exc}")

solution = st.session_state.get("solution")
instance = st.session_state.get("instance")
if solution is None or instance is None:
    st.stop()

metrics = solution.metrics
columns = st.columns(6)
for column, label, value in zip(
    columns,
    ["Orders", "Delivered", "Deferred", "Vehicles used", "Distance (km)", "Mean flow (min)"],
    [
        len(instance.orders),
        metrics.delivered_orders,
        metrics.deferred_orders,
        metrics.vehicles_used,
        f"{metrics.total_distance_metres / 1000:.1f}",
        f"{metrics.mean_flow_time_minutes or 0:.1f}",
    ],
    strict=True,
):
    column.metric(label, value)
st.caption(
    f"{solution.solver_name} · {solution.solver_status.value} · "
    f"{solution.solve_time_seconds:.3f}s · objective {metrics.objective_value:,}"
)

dispatch_tab, workload_tab, tracking_tab, fleet_tab, export_tab = st.tabs(
    ["Dispatch", "Vehicle workload", "Tracking", "Fleet analysis", "Exports"]
)
with dispatch_tab:
    st.info(
        "Route lines are approximate straight segments in Haversine mode."
        if scenario.distance_provider == "haversine"
        else (
            "Distances use the OSRM road-network matrix; map lines remain straight "
            "because the table API does not return route geometry."
        )
    )
    st.pydeck_chart(dispatch_deck(instance, solution), width="stretch")
    st.dataframe(order_results_frame(solution), width="stretch")
with workload_tab:
    st.dataframe(vehicle_results_frame(solution), width="stretch")
    for route in solution.routes:
        with st.expander(route.vehicle_id):
            st.dataframe(pd.DataFrame([asdict(stop) for stop in route.stops]))
with tracking_tab:
    timezone = ZoneInfo(instance.depot.timezone)
    simulation_time = st.slider(
        "Simulation time",
        min_value=instance.planning_time,
        max_value=max(
            (route.route_end_time for route in solution.routes),
            default=instance.planning_time,
        ),
        value=instance.planning_time,
        format="YYYY-MM-DD HH:mm",
    )
    statuses = solution_statuses(solution, simulation_time.astimezone(timezone))
    tracking = order_results_frame(solution)
    tracking["simulation_status"] = tracking["order_id"].map(statuses)
    st.dataframe(tracking, width="stretch")
with fleet_tab:
    maximum = len(instance.vehicles)
    if maximum:
        fleet_range = st.slider("Fleet sizes", 1, maximum, (1, maximum))
        if st.button("Run fleet-size analysis"):
            _, fleet_frame = run_fleet_size_analysis(
                instance,
                get_solver(solver_name),
                solver_config,
                list(range(fleet_range[0], fleet_range[1] + 1)),
            )
            st.dataframe(fleet_frame, width="stretch")
            st.plotly_chart(
                px.line(
                    fleet_frame,
                    x="fleet_size",
                    y=["delivered_orders", "deferred_orders"],
                    markers=True,
                ),
                width="stretch",
            )
            st.plotly_chart(
                px.line(
                    fleet_frame,
                    x="fleet_size",
                    y="total_distance_metres",
                    markers=True,
                ),
                width="stretch",
            )
            st.caption("Distance is not a complete operating-cost measure.")
with export_tab:
    st.download_button(
        "Order results CSV",
        order_results_frame(solution).to_csv(index=False),
        "order_results.csv",
    )
    st.download_button(
        "Vehicle results CSV",
        vehicle_results_frame(solution).to_csv(index=False),
        "vehicle_results.csv",
    )
    st.download_button(
        "Route legs CSV", route_legs_frame(solution).to_csv(index=False), "route_legs.csv"
    )
    st.download_button("Solution JSON", solution_json(solution), "solution.json")
    st.download_button(
        "Scenario YAML",
        yaml.safe_dump(
            {
                "scenario_id": scenario.scenario_id,
                "planning_date": scenario.planning_date.isoformat(),
                "dispatch_cutoff": scenario.dispatch_cutoff.isoformat(),
                "solver": scenario.solver,
                "distance_provider": scenario.distance_provider,
                "random_seed": scenario.random_seed,
            }
        ),
        "scenario.yaml",
    )
