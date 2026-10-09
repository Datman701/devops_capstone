"""Liveness, readiness, root banner and the Prometheus endpoint."""


class TestHealthEndpoints:
    def test_health_returns_ok_without_touching_database(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"]

    def test_ready_reports_database_ok(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "ok"}

    def test_root_advertises_service_metadata(self, client):
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert set(body) >= {"service", "version", "docs", "health", "ready", "metrics"}

    def test_livez_alias(self, client):
        assert client.get("/livez").status_code == 200


class TestMetricsEndpoint:
    def test_metrics_is_prometheus_formatted(self, client):
        client.get("/health")
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_exposes_request_counters(self, client):
        client.get("/health")
        payload = client.get("/metrics").text
        assert "http_requests_total" in payload
        assert "http_request_duration_seconds" in payload

    def test_metrics_records_status_codes(self, client):
        client.get("/api/does-not-exist")
        payload = client.get("/metrics").text
        assert 'status="404"' in payload
