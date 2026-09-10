"""Flask application factory and Discord OAuth routes."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Any, TypeVar, cast
from urllib.parse import urlencode

import httpx
from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for

from .config import Settings
from .supabase_gateway import SupabaseGateway, SupabaseNotConfigured

DISCORD_API = "https://discord.com/api/v10"
DISCORD_AUTHORIZE = "https://discord.com/oauth2/authorize"
MANAGE_GUILD_PERMISSION = 1 << 5

ViewFunction = TypeVar("ViewFunction", bound=Callable[..., Any])


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings.from_env()
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = settings.flask_secret_key
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.public_base_url.startswith("https://"),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )

    gateway = SupabaseGateway(settings)
    app.extensions["guildpilot_settings"] = settings
    app.extensions["guildpilot_supabase"] = gateway

    def require_login(function: ViewFunction) -> ViewFunction:
        @wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if "discord_user" not in session:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "authentication_required"}), 401
                return redirect(url_for("discord_start"))
            return function(*args, **kwargs)

        return cast(ViewFunction, wrapped)

    @app.after_request
    def secure_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        return response

    @app.get("/")
    def index() -> str:
        return render_template(
            "dashboard.html",
            user=session.get("discord_user"),
            guilds=session.get("eligible_guilds", []),
            readiness={
                "supabase": settings.supabase_ready,
                "discord": settings.discord_oauth_ready,
                "session": settings.production_safe,
            },
        )

    @app.get("/api/health")
    def health() -> tuple[Response, int]:
        ready = (
            settings.supabase_ready
            and settings.discord_oauth_ready
            and settings.production_safe
        )
        status_code = 200 if ready else 503
        return (
            jsonify(
                {
                    "service": "guildpilot-web",
                    "status": "ready" if ready else "configuration_required",
                    "checks": {
                        "supabase": settings.supabase_ready,
                        "discord_oauth": settings.discord_oauth_ready,
                        "session_secret": settings.production_safe,
                    },
                }
            ),
            status_code,
        )

    @app.get("/auth/discord/start")
    def discord_start() -> Response | tuple[Response, int]:
        if not settings.discord_oauth_ready:
            return jsonify({"error": "discord_oauth_not_configured"}), 503
        state = secrets.token_urlsafe(32)
        session.clear()
        session["oauth_state"] = state
        session.permanent = True
        query = urlencode(
            {
                "client_id": settings.discord_client_id,
                "redirect_uri": settings.discord_redirect_uri,
                "response_type": "code",
                "scope": "identify guilds",
                "state": state,
                "prompt": "none",
            }
        )
        return redirect(f"{DISCORD_AUTHORIZE}?{query}")

    @app.get("/auth/discord/callback")
    def discord_callback() -> Response | tuple[Response, int]:
        expected_state = session.pop("oauth_state", None)
        supplied_state = request.args.get("state")
        code = request.args.get("code")
        valid_state = bool(
            expected_state
            and supplied_state
            and secrets.compare_digest(expected_state, supplied_state)
        )
        if not valid_state:
            session.clear()
            return jsonify({"error": "invalid_oauth_state"}), 400
        if not code:
            return jsonify({"error": "missing_authorization_code"}), 400

        token_response = httpx.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        if not token_response.is_success:
            return jsonify({"error": "discord_token_exchange_failed"}), 502
        access_token = str(token_response.json()["access_token"])
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(base_url=DISCORD_API, headers=headers, timeout=10.0) as client:
            user_response = client.get("/users/@me")
            guilds_response = client.get("/users/@me/guilds")
        if not user_response.is_success or not guilds_response.is_success:
            return jsonify({"error": "discord_profile_fetch_failed"}), 502

        user = user_response.json()
        guilds = guilds_response.json()
        eligible = [
            {
                "id": str(guild["id"]),
                "name": str(guild["name"]),
                "icon": guild.get("icon"),
                "owner": bool(guild.get("owner")),
            }
            for guild in guilds
            if bool(guild.get("owner"))
            or int(guild.get("permissions", "0")) & MANAGE_GUILD_PERMISSION
        ]

        # Provider tokens are intentionally not placed in Flask's signed cookie session.
        session["discord_user"] = {
            "id": str(user["id"]),
            "username": str(user["username"]),
            "avatar": user.get("avatar"),
        }
        session["eligible_guilds"] = eligible
        session.permanent = True
        return redirect(url_for("index"))

    @app.post("/auth/logout")
    def logout() -> Response:
        session.clear()
        return redirect(url_for("index"))

    @app.get("/api/v1/guilds")
    @require_login
    def guild_list() -> Response:
        return jsonify({"guilds": session.get("eligible_guilds", [])})

    @app.get("/api/v1/guilds/<guild_id>/analytics")
    @require_login
    def guild_analytics(guild_id: str) -> tuple[Response, int] | Response:
        allowed = {str(guild["id"]) for guild in session.get("eligible_guilds", [])}
        if guild_id not in allowed:
            return jsonify({"error": "guild_access_denied"}), 403
        try:
            return jsonify(gateway.analytics_summary(guild_id))
        except SupabaseNotConfigured:
            return jsonify({"error": "supabase_not_configured"}), 503

    @app.post("/api/internal/events")
    def internal_event() -> tuple[Response, int]:
        supplied_key = request.headers.get("X-Internal-Key", "")
        if not settings.internal_api_key or not secrets.compare_digest(
            supplied_key,
            settings.internal_api_key,
        ):
            return jsonify({"error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        event_name = str(payload.get("event_name", "")).strip()
        if not event_name or len(event_name) > 80:
            return jsonify({"error": "invalid_event_name"}), 400
        try:
            event_id = gateway.record_event(
                event_name=event_name,
                guild_id=str(payload["guild_id"]) if payload.get("guild_id") else None,
                actor_id=str(payload["actor_id"]) if payload.get("actor_id") else None,
                properties=(
                    payload.get("properties")
                    if isinstance(payload.get("properties"), dict)
                    else {}
                ),
            )
        except SupabaseNotConfigured:
            return jsonify({"error": "supabase_not_configured"}), 503
        return jsonify({"event_id": event_id, "status": "recorded"}), 201

    return app
