from fastapi.testclient import TestClient
from mytime.main import app


def test_home_returns_ok():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "mytime" in resp.text
