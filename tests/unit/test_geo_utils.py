from decimal import Decimal

import pytest

from utils.geo_utils import calculate_distance, is_within_delivery_zone

TASHKENT = (41.2995, 69.2401)
SAMARKAND = (39.6542, 66.9597)


def test_distance_to_itself_is_zero():
    assert calculate_distance(*TASHKENT, *TASHKENT) == pytest.approx(0.0, abs=1e-9)


def test_distance_is_symmetric():
    assert calculate_distance(*TASHKENT, *SAMARKAND) == pytest.approx(calculate_distance(*SAMARKAND, *TASHKENT))


def test_tashkent_samarkand_is_about_270_km():
    # Great-circle distance between the two city centres is ~270 km.
    assert calculate_distance(*TASHKENT, *SAMARKAND) == pytest.approx(270, rel=0.03)


def test_one_degree_of_latitude_is_about_111_km():
    assert calculate_distance(0, 0, 1, 0) == pytest.approx(111.19, rel=1e-3)


def test_antipodes_are_half_circumference():
    assert calculate_distance(0, 0, 0, 180) == pytest.approx(3.141592653589793 * 6371.0, rel=1e-9)


def _cafe(lat=TASHKENT[0], lon=TASHKENT[1], radius=Decimal("5.00")):
    return {"latitude": lat, "longitude": lon, "delivery_radius_km": radius}


def test_zone_not_configured_accepts_everything():
    assert is_within_delivery_zone(None, *SAMARKAND)
    assert is_within_delivery_zone({}, *SAMARKAND)
    assert is_within_delivery_zone(_cafe(radius=None), *SAMARKAND)
    assert is_within_delivery_zone(_cafe(lat=None), *SAMARKAND)


def test_zone_inside_and_outside():
    near = (TASHKENT[0] + 0.01, TASHKENT[1])  # ~1.1 km north
    far = (TASHKENT[0] + 0.1, TASHKENT[1])  # ~11 km north
    assert is_within_delivery_zone(_cafe(), *near)
    assert not is_within_delivery_zone(_cafe(), *far)


def test_zone_boundary_is_inclusive():
    point = (TASHKENT[0] + 0.01, TASHKENT[1])
    exact = calculate_distance(*TASHKENT, *point)
    assert is_within_delivery_zone(_cafe(radius=exact), *point)
