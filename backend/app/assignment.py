from math import asin, cos, radians, sin, sqrt
from typing import Iterable, Mapping


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    if not all(-90 <= lat <= 90 for lat in (lat1, lat2)):
        raise ValueError("latitude must be between -90 and 90")
    if not all(-180 <= lng <= 180 for lng in (lng1, lng2)):
        raise ValueError("longitude must be between -180 and 180")
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    value = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(value))


def choose_best_agent(
    agents: Iterable[Mapping[str, object]],
    pickup_lat: float,
    pickup_lng: float,
) -> Mapping[str, object] | None:
    candidates: list[tuple[float, Mapping[str, object]]] = []
    for agent in agents:
        if agent.get("status") != "Free":
            continue
        try:
            lat = float(agent["lat"])  # type: ignore[arg-type]
            lng = float(agent["lng"])  # type: ignore[arg-type]
            active_orders = int(agent.get("active_order_count", 0))
            score = haversine_km(pickup_lat, pickup_lng, lat, lng) + 2 * active_orders
        except (KeyError, TypeError, ValueError):
            continue
        candidates.append((score, agent))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None