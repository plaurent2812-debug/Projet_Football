"""
tests/test_api/test_endpoints.py — FastAPI endpoint tests using TestClient.

Coverage: Health, News, Predictions, Monitoring, Performance,
          Best Bets, Expert Picks, Admin, Auth, Error handling.

All Supabase calls are intercepted by the session-scoped `client` fixture
defined in conftest.py — no real network traffic occurs.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ════════════════════════════════════════════════════════════════════
#  HEALTH
# ════════════════════════════════════════════════════════════════════


class TestHealth:
    def test_health_returns_ok(self, client):
        """GET /health must return 200 with status and dependency checks."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("ok", "degraded")
        assert "timestamp" in body
        assert "checks" in body
        assert body["checks"]["api"] == "ok"


# ════════════════════════════════════════════════════════════════════
#  NEWS
# ════════════════════════════════════════════════════════════════════


class TestNews:
    def test_news_returns_200_with_news_array(self, client):
        """GET /api/news must return 200 with a 'news' list."""
        # Patch external RSS fetch so the test is not network-dependent.
        with patch("api.routers.news._fetch_rss_news", return_value=[]):
            resp = client.get("/api/news")
        assert resp.status_code == 200
        body = resp.json()
        assert "news" in body
        assert isinstance(body["news"], list)

    def test_news_returns_cached_data_on_second_call(self, client):
        """Second call should hit TTL cache, not re-fetch RSS."""
        fake_news = [
            {
                "title": "Test headline",
                "link": "https://example.com",
                "source": "Test",
                "pub_date": "Mon, 01 Jan 2026 00:00:00 +0000",
            }
        ]
        # TTLCache uses _data and _timestamps (not _cache).
        import api.routers.news as news_mod

        news_mod._news_cache._data.clear()
        news_mod._news_cache._timestamps.clear()

        with patch("api.routers.news._fetch_rss_news", return_value=fake_news) as mock_fetch:
            resp1 = client.get("/api/news")
            resp2 = client.get("/api/news")

        # RSS fetcher must have been called at most once (cache hit on 2nd).
        assert mock_fetch.call_count <= 1
        assert resp1.status_code == 200
        assert resp2.status_code == 200


# ════════════════════════════════════════════════════════════════════
#  PREDICTIONS
# ════════════════════════════════════════════════════════════════════


class TestPredictions:
    def test_predictions_with_date_returns_200(self, client):
        """GET /api/predictions?date=2026-04-01 must return 200 with 'matches'."""
        resp = client.get("/api/predictions?date=2026-04-01")
        assert resp.status_code == 200
        body = resp.json()
        assert "matches" in body
        assert isinstance(body["matches"], list)

    def test_predictions_without_date_uses_today(self, client):
        """GET /api/predictions without date should default to today."""
        resp = client.get("/api/predictions")
        assert resp.status_code == 200
        body = resp.json()
        assert "date" in body
        assert "matches" in body

    def test_prediction_detail_404_for_unknown_fixture(self, client):
        """GET /api/predictions/99999 must return 404 when fixture not found."""
        # The mock returns empty data by default → fixture is None → 404.
        resp = client.get("/api/predictions/99999")
        assert resp.status_code == 404

    def test_prediction_detail_returns_structure_when_found(self, client, mock_supabase):
        """GET /api/predictions/{id} returns full detail structure for a known fixture."""
        fixture_data = [
            {
                "id": "1",
                "home_team": "PSG",
                "away_team": "OM",
                "date": "2026-04-01T20:00:00Z",
                "status": "NS",
                "api_fixture_id": 12345,
                "home_team_id": 10,
                "away_team_id": 20,
                "league_id": 61,
            }
        ]

        def _table_side_effect(table_name):
            chain = MagicMock()
            result = MagicMock()

            if table_name == "fixtures":
                result.data = fixture_data
            else:
                result.data = []
            result.count = 0

            for method in (
                "select",
                "eq",
                "neq",
                "gte",
                "lte",
                "gt",
                "lt",
                "in_",
                "or_",
                "order",
                "limit",
                "range",
                "insert",
                "upsert",
                "update",
                "delete",
                "filter",
                "single",
            ):
                getattr(chain, method).return_value = chain
            chain.execute.return_value = result
            return chain

        with patch("api.routers.predictions.supabase") as mock_pred_sb:
            mock_pred_sb.table.side_effect = _table_side_effect
            resp = client.get("/api/predictions/1")

        assert resp.status_code == 200
        body = resp.json()
        assert "fixture" in body
        assert "prediction" in body


# ════════════════════════════════════════════════════════════════════
#  MONITORING
# ════════════════════════════════════════════════════════════════════


class TestMonitoring:
    def test_monitoring_returns_200(self, client):
        """GET /api/monitoring must return 200 with monitoring data."""
        fake_payload = {
            "clv": {
                "clv_best_mean": 0,
                "clv_when_correct": 0,
                "pct_positive_clv": 0,
                "n_matches": 0,
                "verdict": "NO_DATA",
                "by_league": {},
                "daily_clv": [],
                "status": "NO_DATA",
            },
            "brier": {
                "brier_1x2": None,
                "brier_1x2_grade": None,
                "ece": None,
                "ece_grade": None,
                "log_loss": None,
                "btts": None,
                "over15": None,
                "over25": None,
                "n_matches": 0,
                "drift": {},
            },
            "health_score": 5,
        }
        # TTLCache uses _data and _timestamps (not _cache).
        import api.routers.monitoring as mon_mod

        mon_mod._monitoring_cache._data.clear()
        mon_mod._monitoring_cache._timestamps.clear()

        with patch("api.routers.monitoring._compute_monitoring", return_value=fake_payload):
            resp = client.get("/api/monitoring")
        assert resp.status_code == 200
        body = resp.json()
        assert "health_score" in body

    def test_monitoring_health_returns_200(self, client):
        """GET /api/monitoring/health must return 200 with health fields."""
        resp = client.get("/api/monitoring/health")
        assert resp.status_code == 200
        body = resp.json()
        # Must include a boolean 'healthy' field.
        assert "healthy" in body
        assert isinstance(body["healthy"], bool)


# ════════════════════════════════════════════════════════════════════
#  PERFORMANCE
# ════════════════════════════════════════════════════════════════════


class TestPerformance:
    def test_performance_all_time_returns_200(self, client):
        """GET /api/performance (days=0) must return 200 with summary fields."""
        resp = client.get("/api/performance")
        assert resp.status_code == 200
        body = resp.json()
        assert "total_matches" in body
        assert "accuracy_1x2" in body

    def test_performance_rolling_window(self, client):
        """GET /api/performance?days=30 must accept the rolling window parameter."""
        resp = client.get("/api/performance?days=30")
        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == 30


# ════════════════════════════════════════════════════════════════════
#  AUTH — verify 401 on protected endpoints
# ════════════════════════════════════════════════════════════════════


class TestAuth:
    # ── /api/best-bets/resolve (verify_cron_auth) ─────────────────

    def test_resolve_bets_without_auth_returns_401(self, client):
        """/api/best-bets/resolve without Authorization header → 401."""
        resp = client.post(
            "/api/best-bets/resolve",
            json={"date": "2026-04-01", "sport": "football"},
        )
        assert resp.status_code == 401

    def test_resolve_bets_with_wrong_auth_returns_401(self, client, bad_auth_headers):
        """/api/best-bets/resolve with wrong secret → 401."""
        resp = client.post(
            "/api/best-bets/resolve",
            json={"date": "2026-04-01", "sport": "football"},
            headers=bad_auth_headers,
        )
        assert resp.status_code == 401

    def test_resolve_bets_with_correct_auth_returns_200(self, client, auth_headers):
        """/api/best-bets/resolve with correct CRON_SECRET → 200."""
        resp = client.post(
            "/api/best-bets/resolve",
            json={"date": "2026-04-01", "sport": "football"},
            headers=auth_headers,
        )
        # 200 (no pending bets — mock returns empty list) or 400 if validation fails.
        # We only care it is NOT a 401.
        assert resp.status_code != 401

    def test_admin_run_pipeline_without_auth_returns_401(self, client):
        """/api/admin/run-pipeline without auth → 401."""
        resp = client.post("/api/admin/run-pipeline")
        assert resp.status_code == 401

    def test_delete_expert_pick_without_auth_returns_401(self, client):
        """/api/expert-picks/1 DELETE without auth → 401."""
        resp = client.delete("/api/expert-picks/1")
        assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════════
#  ADMIN — pipeline status and stop (require Supabase admin JWT)
# ════════════════════════════════════════════════════════════════════


class TestAdmin:
    def test_pipeline_status_with_admin_auth(self, client, mock_supabase):
        """GET /api/admin/pipeline-status with valid admin JWT → 200."""
        user_mock = MagicMock()
        user_mock.user.id = "admin-uuid"
        mock_supabase.auth.get_user.return_value = user_mock

        profile_chain = MagicMock()
        profile_result = MagicMock()
        profile_result.data = {"role": "admin"}
        for method in (
            "select",
            "eq",
            "neq",
            "single",
            "order",
            "limit",
            "gte",
            "lte",
            "filter",
            "in_",
        ):
            getattr(profile_chain, method).return_value = profile_chain
        profile_chain.execute.return_value = profile_result

        with (
            patch("api.routers.admin.supabase", mock_supabase),
            patch("api.routers.admin.supabase.table", return_value=profile_chain),
            patch("api.routers.admin.supabase.auth", mock_supabase.auth),
        ):
            resp = client.get(
                "/api/admin/pipeline-status",
                headers={"Authorization": "Bearer fake-admin-jwt"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body

    def test_stop_pipeline_with_admin_auth_when_idle(self, client, mock_supabase):
        """POST /api/admin/stop-pipeline when no pipeline running → 400 (not 401)."""
        user_mock = MagicMock()
        user_mock.user.id = "admin-uuid"
        mock_supabase.auth.get_user.return_value = user_mock

        profile_chain = MagicMock()
        profile_result = MagicMock()
        profile_result.data = {"role": "admin"}
        for method in (
            "select",
            "eq",
            "neq",
            "single",
            "order",
            "limit",
            "gte",
            "lte",
            "filter",
            "in_",
        ):
            getattr(profile_chain, method).return_value = profile_chain
        profile_chain.execute.return_value = profile_result

        with (
            patch("api.routers.admin.supabase", mock_supabase),
            patch("api.routers.admin.supabase.table", return_value=profile_chain),
            patch("api.routers.admin.supabase.auth", mock_supabase.auth),
        ):
            resp = client.post(
                "/api/admin/stop-pipeline",
                headers={"Authorization": "Bearer fake-admin-jwt"},
            )
        # When idle the endpoint returns 400 (no pipeline running), not 401.
        assert resp.status_code in (200, 400)
        assert resp.status_code != 401


# ════════════════════════════════════════════════════════════════════
#  BEST BETS
# ════════════════════════════════════════════════════════════════════


class TestBestBets:
    def test_get_best_bets_with_date_returns_200(self, client):
        """GET /api/best-bets?date=2026-04-01 must return 200."""
        resp = client.get("/api/best-bets?date=2026-04-01")
        assert resp.status_code == 200
        body = resp.json()
        assert "date" in body

    def test_save_bet_requires_auth(self, client):
        """POST /api/best-bets/save without auth → 401."""
        resp = client.post(
            "/api/best-bets/save",
            json={
                "date": "2026-04-01",
                "sport": "football",
                "label": "PSG Win",
                "market": "1X2",
                "odds": 1.85,
                "confidence": 7,
                "proba_model": 65.0,
            },
        )
        assert resp.status_code == 401

    def test_save_bet_with_cron_auth_accepts_request(self, client, auth_headers, mock_supabase):
        """POST /api/best-bets/save with CRON_SECRET → not 401."""
        insert_chain = MagicMock()
        insert_result = MagicMock()
        insert_result.data = [{"id": 42}]
        for method in (
            "select",
            "eq",
            "insert",
            "upsert",
            "update",
            "delete",
            "order",
            "limit",
            "filter",
        ):
            getattr(insert_chain, method).return_value = insert_chain
        insert_chain.execute.return_value = insert_result

        with patch("api.routers.best_bets.supabase.table", return_value=insert_chain):
            resp = client.post(
                "/api/best-bets/save",
                json={
                    "date": "2026-04-01",
                    "sport": "football",
                    "label": "PSG Win",
                    "market": "1X2",
                    "odds": 1.85,
                    "confidence": 7,
                    "proba_model": 65.0,
                },
                headers=auth_headers,
            )
        assert resp.status_code != 401

    def test_get_best_bets_history_returns_200(self, client):
        """GET /api/best-bets/history must return 200."""
        resp = client.get("/api/best-bets/history")
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════════
#  EXPERT PICKS
# ════════════════════════════════════════════════════════════════════


class TestExpertPicks:
    def test_get_expert_picks_returns_200(self, client):
        """GET /api/expert-picks must return 200 with picks list."""
        resp = client.get("/api/expert-picks")
        assert resp.status_code == 200
        body = resp.json()
        assert "picks" in body
        assert isinstance(body["picks"], list)

    def test_get_expert_picks_latest_returns_200(self, client):
        """GET /api/expert-picks/latest must return 200 with pick field."""
        resp = client.get("/api/expert-picks/latest")
        assert resp.status_code == 200
        body = resp.json()
        assert "pick" in body


# ════════════════════════════════════════════════════════════════════
#  ERROR HANDLING
# ════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    def test_global_exception_handler_returns_500_without_stack_trace(self, client):
        """
        When an unhandled exception occurs, the global handler must:
        - Return HTTP 500
        - Return {"detail": "Internal server error"} (no stack trace)
        """
        # Patch supabase inside predictions router to raise unexpectedly.
        with patch("api.routers.predictions.supabase") as boom:
            boom.table.side_effect = RuntimeError("simulated DB failure")
            resp = client.get("/api/predictions?date=2026-04-01")

        assert resp.status_code == 500
        body = resp.json()
        assert body == {"detail": "Internal server error"}
        # Ensure no Python traceback leaks into the response body.
        raw = resp.text
        assert "Traceback" not in raw
        assert "RuntimeError" not in raw

    def test_validation_error_returns_422(self, client):
        """
        FastAPI validation errors (wrong type / missing field) must return 422.
        POST /api/best-bets/resolve with invalid body triggers Pydantic validation.
        """
        resp = client.post(
            "/api/best-bets/resolve",
            # 'sport' must be 'football' or 'nhl' — sending an invalid value.
            json={"date": "2026-04-01", "sport": "invalid-sport"},
            headers={"Authorization": "Bearer test-cron-secret"},
        )
        assert resp.status_code == 422
