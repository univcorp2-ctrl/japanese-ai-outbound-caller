from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.storage import SQLiteStore


def make_client(tmp_path):
    settings = Settings(
        database_path=str(tmp_path / "test.db"),
        dry_run=True,
        enforce_business_hours=False,
        recipient_cooldown_days=0,
        max_calls_per_day=10,
        internal_api_key="test-internal",
    )
    store = SQLiteStore(settings.database_path)
    return TestClient(create_app(settings=settings, store=store)), settings


def valid_request(phone="+819012345678"):
    return {
        "phone_number": phone,
        "recipient_name": "山田太郎",
        "purpose": "依頼された製品デモの日程確認",
        "consent_basis": "requested_callback",
        "context": {"preferred_date": "2026-07-10"},
    }


def test_health_and_dry_run_dispatch(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.get("/healthz").json() == {"status": "ok", "dry_run": True}

    response = client.post("/v1/calls", json=valid_request())
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "dispatched"
    assert body["phone_masked"].endswith("5678")
    assert body["room_name"].startswith("dry-run-")

    fetched = client.get(f"/v1/calls/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_invalid_phone_is_rejected(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post("/v1/calls", json=valid_request("090-1234-5678"))
    assert response.status_code == 422


def test_opt_out_blocks_future_calls(tmp_path):
    client, settings = make_client(tmp_path)
    response = client.post(
        "/v1/internal/opt-outs",
        headers={"X-Internal-API-Key": settings.internal_api_key},
        json={"phone_number": "+819012345678", "reason": "no_more_calls"},
    )
    assert response.status_code == 204

    blocked = client.post("/v1/calls", json=valid_request())
    assert blocked.status_code == 409


def test_internal_endpoint_requires_key(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post(
        "/v1/internal/opt-outs",
        json={"phone_number": "+819012345678", "reason": "test"},
    )
    assert response.status_code == 401


def test_daily_limit(tmp_path):
    settings = Settings(
        database_path=str(tmp_path / "limit.db"),
        dry_run=True,
        enforce_business_hours=False,
        recipient_cooldown_days=0,
        max_calls_per_day=1,
    )
    store = SQLiteStore(settings.database_path)
    client = TestClient(create_app(settings=settings, store=store))
    assert client.post("/v1/calls", json=valid_request()).status_code == 202
    second = client.post("/v1/calls", json=valid_request("+819012345679"))
    assert second.status_code == 429


def test_timestamp_is_iso8601(tmp_path):
    client, _ = make_client(tmp_path)
    body = client.post("/v1/calls", json=valid_request()).json()
    parsed = datetime.fromisoformat(body["created_at"])
    assert parsed.tzinfo == UTC
