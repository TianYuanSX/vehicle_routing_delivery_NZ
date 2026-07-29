# Acceptance Results

Verified on 2026-07-29 with Python 3.12.13, `uv` 0.11.31, offline
Haversine matrices, and mocked OSRM HTTP behavior.

| Acceptance criteria | Result | Evidence |
|---|---|---|
| AT-DATA-001 through AT-DATA-005 | Pass | CSV/domain tests cover valid input, structured and legacy addresses, duplicates, coordinates, shifts, oversized warnings, missing columns, empty/mixed rows, and depot references. |
| AT-SOLVER-001 through AT-SOLVER-010 | Pass | Shared parametrized tests exercise both solvers; `validate_solution` checks representation, uniqueness, depot boundaries, capacity, shifts, distance, and objective reconciliation. |
| AT-ETA-001 through AT-ETA-005 | Pass | Shared route evaluation accumulates travel/service, emits departure and return timestamps, enforces the return deadline, and computes flow from original creation. |
| AT-MULTI-001 through AT-MULTI-004 | Pass | Deterministic three-day test covers carry-over, cutoff eligibility, added capacity, preserved timestamps, and exactly-once delivery. |
| AT-UI-001 | Pass | Streamlit AppTest loaded the default and all three Manual tables (depot, orders, and vehicles) and solved the ten-location geocoded Wellington default with no exceptions; fixtures verify editable depot conversion, complete public address fields, and distinct Wellington coordinates. |
| AT-UI-002 | Pass | All UI ingestion paths use tested whole-file validation and show caught validation errors before solving. |
| AT-UI-003 | Pass | `map_view` is tested with non-Wellington coordinates and derives center/zoom from all coordinates. |
| AT-UI-004 and AT-UI-005 | Pass | App renders full order and every-vehicle result frames from the common solution; used and unused vehicle metrics are generated together. |
| AT-UI-006 | Pass | Export tests reconcile order, vehicle, and route-leg frames with the solution; the UI exposes all three CSV downloads plus JSON/YAML. |
| AT-FLEET-001 through AT-FLEET-004 | Pass | Seeded repeat test compares tidy runs; implementation changes only the vehicle prefix and makes no monotonicity claim. |
| AT-COMP-001 through AT-COMP-003 | Pass | Registry solvers consume the identical `RoutingInstance` and return `RoutingSolution`; feasibility is validated before presentation. |
| Performance targets | Pass for prototype smoke scope | A generated 50-order/10-vehicle offline instance and the Wellington scenarios were executed during final verification; configured OR-Tools time limits are passed directly to the search. |

The normal test suite is deterministic and makes no external routing calls.
