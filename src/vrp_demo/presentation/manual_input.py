from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from vrp_demo.domain.models import Depot, Order


def depot_to_manual_frame(depot: Depot) -> pd.DataFrame:
    """Convert the single prototype depot to the editable input schema."""
    return pd.DataFrame(
        [
            {
                "depot_id": depot.depot_id,
                "name": depot.name,
                "address": getattr(depot, "address", ""),
                "suburban": getattr(depot, "suburban", ""),
                "city": getattr(depot, "city", ""),
                "latitude": depot.latitude,
                "longitude": depot.longitude,
                "timezone": depot.timezone,
            }
        ]
    )


def orders_to_manual_frame(orders: Iterable[Order]) -> pd.DataFrame:
    """Convert orders to the editable input schema.

    The attribute checks keep a hot-reloaded Streamlit session compatible with
    Order instances created before the structured address fields were added.
    """
    rows: list[dict[str, object]] = []
    for order in orders:
        is_legacy_address = not hasattr(order, "suburban")
        rows.append(
            {
                "order_id": order.order_id,
                "latitude": order.latitude,
                "longitude": order.longitude,
                "size": order.size,
                "order_created_time": order.order_created_time.isoformat(),
                "service_minutes": order.service_seconds // 60,
                "priority": order.priority,
                "customer_name": getattr(order, "customer_name", ""),
                "suburban": (
                    getattr(order, "address", "")
                    if is_legacy_address
                    else getattr(order, "suburban", "")
                ),
                "address": "" if is_legacy_address else getattr(order, "address", ""),
                "city": getattr(order, "city", ""),
            }
        )
    return pd.DataFrame(rows)
