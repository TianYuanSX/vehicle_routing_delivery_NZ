# Assumptions

These decisions apply to prototype one and should be reviewed before production use.

- Capacity is a single integer quantity whose scenario label defaults to `cartons`.
- Internal distance and duration units are integer metres and integer seconds.
- The default Haversine road-speed approximation is 35 km/h; map lines in this mode
  are explicitly labelled approximate.
- Order service defaults to five minutes when absent from input.
- Priority is an integer from 1 (normal) to 5 (highest).
- Dispatch occurs at the configured cutoff on the planning date in the depot's IANA
  timezone. Orders created after that instant are eligible the next day.
- Routes depart at the later of the vehicle shift start and dispatch cutoff.
- Arrival is the instant a vehicle reaches an order. Departure is arrival plus service
  duration; waiting and customer time windows are not modelled.
- Deferred orders retain their original creation time and therefore accrue age cost
  naturally across planning days.
- The default weighted objective uses a base deferral weight of 1,000,000, age cost
  of 10,000 per full day, priority cost of 5,000 per priority point, flow-time weight
  10 per minute, and distance weight 1 per metre.
- Solver results marked `FEASIBLE` are not claims of global optimality.
- Fleet operating cost is reported only when vehicle costs are supplied; it is fixed
  daily cost for used vehicles plus route kilometres times vehicle cost per kilometre.
- Static tracking is derived from planned timestamps and a user-controlled clock; it
  is not live GPS tracking.

