import pytest

from app.assignment import choose_best_agent, haversine_km


def test_haversine_same_point_is_zero():
    assert haversine_km(19.0, 72.0, 19.0, 72.0) == pytest.approx(0)


def test_assignment_uses_distance_and_active_order_penalty():
    agents = [
        {"id": 1, "status": "Free", "lat": 19.0, "lng": 72.0, "active_order_count": 3},
        {"id": 2, "status": "Free", "lat": 19.001, "lng": 72.001, "active_order_count": 0},
        {"id": 3, "status": "Busy", "lat": 19.0, "lng": 72.0, "active_order_count": 0},
    ]
    assert choose_best_agent(agents, 19.0, 72.0)["id"] == 2


def test_assignment_skips_invalid_coordinates_and_non_free_agents():
    assert choose_best_agent(
        [{"id": 1, "status": "Free", "lat": None, "lng": 72, "active_order_count": 0}],
        19,
        72,
    ) is None
