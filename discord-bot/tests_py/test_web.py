from server.guildpilot.app import create_app
from server.guildpilot.config import Settings


def settings() -> Settings:
    return Settings(
        flask_secret_key="x" * 40,
        public_base_url="http://localhost:5000",
        internal_api_key="internal-test-key",
        discord_client_id="",
        discord_client_secret="",
        discord_redirect_uri="http://localhost:5000/auth/discord/callback",
        supabase_url="",
        supabase_secret_key="",
    )


def test_health_reports_missing_connections_without_fake_success() -> None:
    app = create_app(settings())
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json["status"] == "configuration_required"
    assert response.json["checks"] == {
        "supabase": False,
        "discord_oauth": False,
        "session_secret": True,
    }


def test_internal_events_require_a_server_key() -> None:
    app = create_app(settings())
    client = app.test_client()

    response = client.post("/api/internal/events", json={"event_name": "value_event"})

    assert response.status_code == 401
    assert response.json == {"error": "unauthorized"}


def test_dashboard_has_security_headers() -> None:
    app = create_app(settings())
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert b"No invented success" in response.data

