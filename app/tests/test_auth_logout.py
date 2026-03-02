from fastapi.testclient import TestClient

from app.main import app


def test_logout_clears_auth_cookies() -> None:
    with TestClient(app) as client:
        response = client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == "Logout successful"
    cookie_headers = response.headers.get_list("set-cookie")
    assert any("access_token=" in item and "Max-Age=0" in item for item in cookie_headers)
    assert any("refresh_token=" in item and "Max-Age=0" in item for item in cookie_headers)
