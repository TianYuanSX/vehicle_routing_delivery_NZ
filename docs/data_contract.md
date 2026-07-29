# Data Contract

## 1. General conventions

- CSV files use UTF-8 encoding.
- Column names use `snake_case`.
- Identifiers are strings and must be unique within their entity type.
- Timestamps use ISO 8601 with timezone information.
- Internal distances use integer metres.
- Internal durations use integer seconds.
- Capacity values are non-negative integers in a scenario-defined unit.
- Coordinates use decimal degrees in WGS84.

## 2. Orders input

Default filename: `orders.csv`

### Required columns

| Column | Type | Rules |
|---|---|---|
| `order_id` | string | Unique, non-empty |
| `latitude` | float | Between -90 and 90 |
| `longitude` | float | Between -180 and 180 |
| `size` | integer | Greater than 0 |
| `order_created_time` | timestamp | Timezone-aware ISO 8601 |

### Optional columns

| Column | Type | Default | Description |
|---|---|---|---|
| `service_minutes` | integer | Scenario default | Time at destination |
| `priority` | integer | 1 | Higher means more important |
| `status` | string | `PENDING` | Initial status |
| `customer_name` | string | empty | Public location or customer display name |
| `suburban` | string | empty | Suburb or local area |
| `address` | string | empty | Number and street name |
| `city` | string | empty | City name |
| `notes` | string | empty | Display-only field |

### Example

```csv
order_id,customer_name,suburban,address,city,latitude,longitude,size,order_created_time,service_minutes,priority
ORD-001,Museum of New Zealand Te Papa Tongarewa,Te Aro,55 Cable Street,Wellington,-41.2903326,174.7819275,12,2026-07-22T14:30:00+12:00,5,1
ORD-002,PAK'nSAVE Kilbirnie,Kilbirnie,78 Rongotai Road,Wellington,-41.3183504,174.7964823,8,2026-07-23T07:15:00+12:00,7,2
```

### Address-field migration

Earlier prototype files used `address` as a suburb/display label. New files should
put that value in `suburban`, use `address` for the number and street name, and
put the city in `city`. For backward compatibility, when neither `suburban` nor
the accepted alias `suburb` is present, the loader treats the legacy `address`
value as `suburban` and leaves the structured street address empty.

## 3. Vehicles input

Default filename: `vehicles.csv`

### Required columns

| Column | Type | Rules |
|---|---|---|
| `vehicle_id` | string | Unique, non-empty |
| `capacity` | integer | Greater than 0 |
| `shift_start` | local time or timestamp | Must precede shift end |
| `shift_end` | local time or timestamp | Must follow shift start |
| `depot_id` | string | Must match an existing depot |

### Optional columns

| Column | Type | Default | Description |
|---|---|---|---|
| `active` | boolean | true | Whether available for planning |
| `driver_id` | string | Same as vehicle ID | Driver identifier |
| `cost_per_km` | decimal | 0 | Variable operating cost |
| `fixed_daily_cost` | decimal | 0 | Fixed daily vehicle cost |
| `speed_factor` | decimal | 1.0 | Future travel-time multiplier |

### Example

```csv
vehicle_id,capacity,shift_start,shift_end,depot_id,active,cost_per_km,fixed_daily_cost
VAN-01,40,08:00,17:00,WLG-DEPOT,true,0.85,120
VAN-02,55,08:00,17:00,WLG-DEPOT,true,0.95,140
```

## 4. Depot input

Default filename: `depots.csv`

Prototype one requires exactly one depot.

| Column | Type | Rules |
|---|---|---|
| `depot_id` | string | Unique, non-empty |
| `name` | string | Non-empty |
| `latitude` | float | Between -90 and 90 |
| `longitude` | float | Between -180 and 180 |
| `timezone` | string | Valid IANA timezone |

Optional display fields are `address` (number and street), `suburban`, and `city`.

### Example

```csv
depot_id,name,address,suburban,city,latitude,longitude,timezone
WLG-DEPOT,NZ Post Wellington Super Depot,8 Carmel Terrace,Grenada Village,Wellington,-41.2007115,174.8255637,Pacific/Auckland
```

## 5. Scenario configuration

Recommended filename: `scenario.yaml`

```yaml
scenario_id: wellington-demo
planning_date: 2026-07-23
dispatch_cutoff: "08:00"
default_service_minutes: 5
capacity_unit: cartons
distance_provider: haversine
solver: ortools
solver_time_limit_seconds: 10
random_seed: 42

objective:
  deferred_weight: 1000000
  flowtime_weight: 10
  distance_weight: 1
  age_penalty_per_day: 10000
  priority_penalty: 5000
```

## 6. Order-results output

Recommended filename: `order_results.csv`

Every input order must appear exactly once.

| Column | Type | Description |
|---|---|---|
| `order_id` | string | Original order ID |
| `planning_date` | date | Date of planning run |
| `planning_status` | enum | `PLANNED` or `DEFERRED` |
| `simulation_status` | enum | Optional current simulated status |
| `vehicle_id` | nullable string | Assigned vehicle |
| `stop_sequence` | nullable integer | Delivery order within route |
| `estimated_arrival_time` | nullable timestamp | Planned arrival |
| `estimated_departure_time` | nullable timestamp | Arrival plus service duration |
| `flow_time_minutes` | nullable integer | ETA minus original creation time |
| `deferred_reason_code` | nullable enum | Machine-readable reason |
| `deferred_reason` | nullable string | Human-readable explanation |
| `solver_name` | string | Solver that created result |

### Deferred reason codes

Recommended initial values:

- `ORDER_EXCEEDS_ALL_VEHICLE_CAPACITIES`
- `INSUFFICIENT_TOTAL_CAPACITY`
- `SHIFT_TIME_INFEASIBLE`
- `NO_ACTIVE_VEHICLE`
- `SOLVER_DROPPED_WITH_PENALTY`
- `SOLVER_TIMEOUT_NO_FEASIBLE_ASSIGNMENT`
- `INVALID_ORDER`

## 7. Vehicle-results output

Recommended filename: `vehicle_results.csv`

Every input vehicle should appear, including unused vehicles.

| Column | Type | Description |
|---|---|---|
| `vehicle_id` | string | Vehicle ID |
| `used` | boolean | Whether route contains an order |
| `order_count` | integer | Number of assigned orders |
| `assigned_load` | integer | Sum of order sizes |
| `capacity` | integer | Vehicle capacity |
| `capacity_utilization` | decimal | Assigned load divided by capacity |
| `route_distance_metres` | integer | Full route distance |
| `travel_seconds` | integer | Driving time |
| `service_seconds` | integer | Stop service time |
| `route_duration_seconds` | integer | Return time minus departure time |
| `shift_duration_seconds` | integer | Configured shift length |
| `shift_utilization` | decimal | Route duration divided by shift length |
| `route_start_time` | nullable timestamp | Departure from depot |
| `route_end_time` | nullable timestamp | Return to depot |

## 8. Route-leg output

Recommended filename: `route_legs.csv`

| Column | Type | Description |
|---|---|---|
| `vehicle_id` | string | Assigned vehicle |
| `leg_sequence` | integer | Sequence starting at 1 |
| `from_location_id` | string | Depot or order ID |
| `to_location_id` | string | Depot or order ID |
| `distance_metres` | integer | Leg distance |
| `travel_seconds` | integer | Leg travel time |
| `arrival_time` | timestamp | Arrival at destination |
| `departure_time` | timestamp | Departure after service |
| `load_before` | integer | Physical onboard load before destination |
| `load_after` | integer | Physical onboard load after destination |

## 9. Solution metadata output

Recommended filename: `solution_metadata.json`

```json
{
  "scenario_id": "wellington-demo",
  "solver_name": "ortools",
  "solver_status": "FEASIBLE",
  "solve_time_seconds": 3.42,
  "solver_time_limit_seconds": 10,
  "objective_value": 1048230,
  "objective_components": {
    "deferred_cost": 1000000,
    "flowtime_cost": 42000,
    "distance_cost": 6230
  },
  "distance_provider": "haversine",
  "random_seed": 42
}
```

## 10. Validation behaviour

### Fatal errors

The solver must not run when:

- Required columns are missing.
- IDs are duplicated.
- Coordinates are invalid.
- Timestamps cannot be parsed.
- A vehicle shift is invalid.
- No depot exists.
- More than one depot exists in prototype one.

### Warnings

The solver may run but should warn when:

- An order exceeds every active vehicle's capacity.
- No vehicles are active.
- All orders were created after the dispatch cutoff.
- The distance provider falls back from OSRM to Haversine.
- Objective weights appear poorly scaled.
