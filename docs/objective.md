# Objective and KPI Definition

## 1. Objective hierarchy

The planning objective has three business priorities:

1. Avoid deferring orders, especially old or high-priority orders.
2. Reduce order flow time.
3. Reduce total fleet distance.

Distance cannot be the only objective because the minimum-distance solution would defer every order when dropping is allowed.

## 2. Recommended weighted objective

For prototype one:

\[
\text{Objective} =
\text{DeferredCost} +
\text{FlowTimeCost} +
\text{DistanceCost}
\]

where:

\[
\text{DeferredCost}
=
\sum_{i \in D}
\left(
W_d +
W_a \times \text{ageDays}_i +
W_p \times \text{priority}_i
\right)
\]

\[
\text{FlowTimeCost}
=
W_f \sum_{i \in P}
\text{flowTimeMinutes}_i
\]

\[
\text{DistanceCost}
=
W_m \times \text{totalDistanceMetres}
\]

Definitions:

- `D`: deferred orders.
- `P`: planned orders.
- `ageDays`: full or fractional days from creation to planning time.
- `flowTimeMinutes`: estimated arrival minus original order creation time.

## 3. Initial weight guidance

Example starting weights:

```yaml
objective:
  deferred_weight: 1000000
  age_penalty_per_day: 10000
  priority_penalty: 5000
  flowtime_weight: 10
  distance_weight: 1
```

These values are illustrative. They must be calibrated to the scale of the scenario.

A practical requirement is:

> The cost of deferring one normal order should normally exceed the largest plausible distance and flow-time improvement from dropping that order.

## 4. Lexicographic interpretation

The business intent is lexicographic:

1. Minimize weighted deferred orders.
2. Subject to that, minimize total flow time.
3. Subject to that, minimize distance.

A single weighted sum approximates this hierarchy. Later implementations may perform sequential optimization passes for stricter lexicographic behaviour.

## 5. Flow time

For order `i`:

\[
\text{flowTime}_i = \text{ETA}_i - \text{orderCreatedTime}_i
\]

Flow time includes:

- Time spent waiting before the planning day.
- Time between dispatch and arrival.
- Any previous-day backlog delay.

Deferred orders do not have an ETA on the current planning day. Their service impact is represented through the deferred penalty and backlog age.

## 6. Why optimize total flow time instead of mean flow time

Reporting metric:

\[
\text{MeanFlowTime} =
\frac{\sum_{i \in P}\text{flowTime}_i}{|P|}
\]

When the delivered set is fixed, minimizing total flow time and mean flow time are equivalent. When the delivered set can change, directly minimizing mean flow time can reward dropping slower orders. Therefore:

- Optimize total flow time.
- Report mean flow time.

## 7. Distance objective

Total fleet distance is:

\[
\text{TotalDistance} =
\sum_{v \in V}\sum_{(a,b) \in R_v} d_{ab}
\]

It includes:

- Depot to first stop.
- Every delivery-to-delivery leg.
- Final stop to depot.

Unused vehicles contribute zero distance.

## 8. Future operating cost objective

Distance is only a partial cost measure. A later version should use:

\[
\text{OperatingCost} =
\sum_v
\left(
\text{fixedDailyCost}_v \times \text{used}_v +
\text{costPerKm}_v \times \text{routeKm}_v
\right)
\]

Possible additions:

- Driver labour cost.
- Overtime cost.
- Fuel or energy cost.
- Vehicle-specific maintenance cost.
- Carbon cost.

## 9. Fairness and starvation prevention

An order should become increasingly expensive to defer. The initial mechanism is age-based penalty.

Recommended additional safeguards:

- Increase penalty each deferred day.
- Use oldest-created-time ordering in the baseline.
- Report the oldest backlog age.
- Add a service-level KPI for orders older than a threshold.

## 10. KPI definitions

### Service KPIs

- **Delivered orders**: number planned today.
- **Deferred orders**: number not planned today.
- **Delivery rate**: delivered divided by eligible orders.
- **Mean flow time**: average ETA minus creation time for delivered orders.
- **Maximum flow time**: largest delivered-order flow time.
- **Oldest backlog age**: age of the oldest deferred order.

### Fleet KPIs

- **Vehicles used**: number of non-empty routes.
- **Total distance**: sum of all route distances.
- **Average capacity utilization**: assigned load divided by capacity, averaged over used vehicles unless otherwise stated.
- **Average shift utilization**: route duration divided by shift duration, averaged over used vehicles.
- **Orders per used vehicle**: delivered orders divided by vehicles used.

### Solver KPIs

- Solver status.
- Objective value.
- Objective components.
- Runtime.
- Time limit.
- Random seed.

## 11. Objective consistency checks

The implementation should verify:

- Objective value equals the sum of reported objective components.
- Total flow time equals the sum of delivered-order flow times.
- Distance cost uses the same units and scale documented in configuration.
- Deferred penalties use original creation times rather than the latest deferral date.
