from contextlib import contextmanager
from io import BytesIO

from fastapi.testclient import TestClient

from app import main


def test_order_validation_rejects_bad_coordinates():
    response = TestClient(main.app).post(
        "/orders",
        json={
            "name": "Test Customer",
            "email": "test@example.com",
            "item": "Book",
            "pickup_lat": 100,
            "pickup_lng": 72,
            "drop_address": "Mumbai",
        },
    )
    assert response.status_code == 422


def test_invalid_order_id_is_not_found(monkeypatch):
    monkeypatch.setattr(main.db, "fetch_one", lambda *args: None)
    response = TestClient(main.app).get("/orders/99999")
    assert response.status_code == 404


def test_invalid_status_transition(monkeypatch):
    monkeypatch.setattr(main, "_get_order", lambda order_id: {"id": order_id, "status": "Delivered"})
    response = TestClient(main.app).post("/orders/1/out-for-delivery")
    assert response.status_code == 409


def test_proof_key_uses_contract_format():
    assert main.proof_key_for_order(2) == "proof/order-2.jpg"


def test_non_jpeg_proof_is_rejected_without_upload(monkeypatch):
    monkeypatch.setattr(
        main,
        "_get_order",
        lambda order_id: {"id": order_id, "status": "Out for Delivery", "agent_id": 4},
    )
    uploaded = []
    monkeypatch.setattr(main.aws_clients, "upload_proof", lambda *args: uploaded.append(args))

    response = TestClient(main.app).post(
        "/orders/2/proof",
        files={"file": ("proof.png", BytesIO(b"not-a-jpeg"), "image/png")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Delivery proof must be a JPEG image"
    assert uploaded == []


def test_jpeg_proof_uses_contract_key_and_stores_it(monkeypatch):
    monkeypatch.setattr(
        main,
        "_get_order",
        lambda order_id: {"id": order_id, "status": "Out for Delivery", "agent_id": 4},
    )
    uploaded = []
    statements = []
    monkeypatch.setattr(
        main.aws_clients,
        "upload_proof",
        lambda fileobj, key, content_type: uploaded.append(
            (fileobj.read(), key, content_type)
        ),
    )
    monkeypatch.setattr(main.aws_clients, "notify", lambda *args: None)

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, sql, params=()):
            statements.append((sql, params))

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def cursor(self):
            return Cursor()

        def commit(self):
            return None

    monkeypatch.setattr(main.db, "connection", lambda: Connection())

    response = TestClient(main.app).post(
        "/orders/8/proof",
        files={
            "file": (
                "delivery.jpeg",
                BytesIO(b"\xff\xd8\xffjpeg-bytes"),
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "Delivered", "proof_key": "proof/order-8.jpg"}
    assert uploaded == [
        (b"\xff\xd8\xffjpeg-bytes", "proof/order-8.jpg", "image/jpeg")
    ]
    assert any("proof/order-8.jpg" in params for _, params in statements)


def test_local_proof_route_serves_the_stored_key(tmp_path, monkeypatch):
    settings = main.get_settings()
    monkeypatch.setattr(settings, "smartflow_local", True)
    monkeypatch.setattr(settings, "local_s3_dir", str(tmp_path))
    proof = tmp_path / "proof" / "order-8.jpg"
    proof.parent.mkdir()
    proof.write_bytes(b"stored-jpeg")

    response = TestClient(main.app).get("/local-proof/proof/order-8.jpg")

    assert response.status_code == 200
    assert response.content == b"stored-jpeg"


def test_order_response_includes_history_and_agent(monkeypatch):
    monkeypatch.setattr(
        main.db,
        "fetch_one",
        lambda *args: {
            "id": 1,
            "status": "Assigned",
            "agent_name": "Priya",
            "item": "Book",
        },
    )
    monkeypatch.setattr(
        main.db,
        "fetch_all",
        lambda *args: [{"status": "Placed", "changed_at": "2026-01-01T00:00:00"}],
    )
    response = TestClient(main.app).get("/orders/1")
    assert response.status_code == 200
    assert response.json()["agent_name"] == "Priya"
    assert response.json()["history"][0]["status"] == "Placed"


def test_agents_contract(monkeypatch):
    monkeypatch.setattr(
        main.db,
        "fetch_all",
        lambda *args: [{"id": 1, "name": "Ravi", "status": "Free"}],
    )
    response = TestClient(main.app).get("/agents")
    assert response.json() == [{"id": 1, "name": "Ravi", "status": "Free"}]


def test_agent_status_contract(monkeypatch):
    monkeypatch.setattr(main.db, "fetch_one", lambda *args: {"id": 1})
    monkeypatch.setattr(main.db, "execute", lambda *args: 1)
    response = TestClient(main.app).post("/agents/1/status", json={"status": "Busy"})
    assert response.json() == {"ok": True}


def test_analytics_contract(monkeypatch):
    fetch_all_results = iter(
        [
            [{"status": "Placed", "count": 2}],
            [{"name": "Ravi", "count": 1}],
        ]
    )
    monkeypatch.setattr(main.db, "fetch_all", lambda *args: next(fetch_all_results))
    monkeypatch.setattr(
        main.db,
        "fetch_one",
        lambda *args: {"avg_delivery_minutes": 12.5},
    )
    response = TestClient(main.app).get("/analytics")
    assert response.json() == {
        "by_status": {"Placed": 2},
        "per_agent": {"Ravi": 1},
        "avg_delivery_minutes": 12.5,
    }


def test_analytics_uses_positive_placed_to_delivered_duration(monkeypatch):
    average_query = []
    queries = []
    monkeypatch.setattr(
        main.db,
        "fetch_all",
        lambda sql, *args: queries.append(sql) or [{"status": "Delivered", "count": 1}]
        if "GROUP BY status" in sql
        else [{"name": "Imran", "count": 1}],
    )
    monkeypatch.setattr(
        main.db,
        "fetch_one",
        lambda sql, *args: average_query.append(sql) or {"avg_delivery_minutes": 9.3667},
    )

    response = TestClient(main.app).get("/analytics")

    assert response.status_code == 200
    assert response.json()["avg_delivery_minutes"] == 9.3667
    assert "TIMESTAMPDIFF(SECOND" in average_query[0]
    assert "placed.changed_at" in average_query[0]
    assert "delivered.changed_at" in average_query[0]


def test_analytics_average_supports_multiple_delivered_orders(monkeypatch):
    results = iter([[], []])
    monkeypatch.setattr(main.db, "fetch_all", lambda *args: next(results))
    monkeypatch.setattr(main.db, "fetch_one", lambda *args: {"avg_delivery_minutes": 7.5})

    response = TestClient(main.app).get("/analytics")

    assert response.json()["avg_delivery_minutes"] == 7.5


def test_analytics_returns_none_when_no_orders_are_delivered(monkeypatch):
    results = iter([[], []])
    monkeypatch.setattr(main.db, "fetch_all", lambda *args: next(results))
    monkeypatch.setattr(main.db, "fetch_one", lambda *args: {"avg_delivery_minutes": None})

    response = TestClient(main.app).get("/analytics")

    assert response.json()["avg_delivery_minutes"] is None


def test_order_database_failure_is_logged_without_exposing_details(monkeypatch, caplog):
    @contextmanager
    def failing_connection():
        raise RuntimeError("database connection failed")
        yield

    monkeypatch.setattr(main.db, "connection", failing_connection)
    client = TestClient(main.app, raise_server_exceptions=False)
    with caplog.at_level("ERROR", logger="app.main"):
        response = client.post(
            "/orders",
            json={
                "name": "Test Customer",
                "email": "failure@example.com",
                "item": "Book",
                "pickup_lat": 19.076,
                "pickup_lng": 72.878,
                "drop_address": "Mumbai",
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Unable to create order"}
    assert "Order creation failed" in caplog.text
    assert "database connection failed" in caplog.text
