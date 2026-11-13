"""Geographic helpers (pure functions, no I/O)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

EARTH_RADIUS_KM = 6371.0


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres (haversine formula)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def is_within_delivery_zone(cafe_settings: Mapping[str, Any] | None, lat: float, lon: float) -> bool:
    """True when (lat, lon) is inside the configured delivery radius.

    If the cafe location or the radius has not been configured yet, every
    location is accepted (same behaviour as before the zone feature existed).
    """
    if not cafe_settings:
        return True
    cafe_lat = cafe_settings.get("latitude")
    cafe_lon = cafe_settings.get("longitude")
    radius = cafe_settings.get("delivery_radius_km")
    if cafe_lat is None or cafe_lon is None or radius is None:
        return True
    return calculate_distance(float(cafe_lat), float(cafe_lon), lat, lon) <= float(radius)
