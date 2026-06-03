import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_orders_empty():
    r = client.get("/orders")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_order():
    r = client.post("/orders", json={"item": "widget", "quantity": 3})
    assert r.status_code == 201
    data = r.json()
    assert data["item"] == "widget"
    assert data["quantity"] == 3
    assert "id" in data


def test_get_order():
    r = client.post("/orders", json={"item": "gadget", "quantity": 1})
    order_id = r.json()["id"]

    r = client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    assert r.json()["item"] == "gadget"


def test_get_nonexistent_order():
    r = client.get("/orders/99999")
    assert r.status_code == 404


def test_metrics_endpoint():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert b"http_requests_total" in r.content


def test_chaos_random():
    r = client.post("/chaos")
    assert r.status_code == 200
    assert r.json()["status"] == "chaos activated"
    client.post("/chaos", json={"mode": "reset"})


def test_chaos_specific():
    r = client.post("/chaos", json={"mode": "cpu_spike"})
    assert r.status_code == 200
    assert r.json()["mode"] == "cpu_spike"
    client.post("/chaos", json={"mode": "reset"})


def test_chaos_reset():
    client.post("/chaos", json={"mode": "cpu_spike"})
    r = client.post("/chaos", json={"mode": "reset"})
    assert r.status_code == 200
    assert r.json()["mode"] == "reset"


def test_chaos_invalid_mode():
    r = client.post("/chaos", json={"mode": "explode"})
    assert r.status_code == 400
