from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import __version__
from app.config import Settings, get_settings
from app.main import app
from tests.helpers import IsolatedSettings


@pytest.fixture
def client() -> Iterator[TestClient]:
    def fake_settings() -> Settings:
        return IsolatedSettings(
            app_name="Test App",
            environment="test",
            database_url="sqlite:///./secret-marker.db",
        )

    app.dependency_overrides[get_settings] = fake_settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "Test App",
        "environment": "test",
        "version": __version__,
    }


def test_health_does_not_expose_database_url(client: TestClient) -> None:
    response = client.get("/api/health")
    assert "secret-marker" not in response.text


def test_health_only_allows_get(client: TestClient) -> None:
    assert client.post("/api/health").status_code == 405


def test_unknown_route_returns_404(client: TestClient) -> None:
    assert client.get("/api/does-not-exist").status_code == 404
