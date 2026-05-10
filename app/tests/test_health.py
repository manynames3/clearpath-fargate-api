async def test_health_is_liveness_only(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "clearpath-api"}


async def test_ready_checks_database(client):
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "clearpath-api"}


async def test_ready_returns_503_when_database_unavailable(client, monkeypatch):
    async def fail_ready_check():
        raise RuntimeError("database down")

    monkeypatch.setattr("src.main.check_database_ready", fail_ready_check)

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "database unavailable"
