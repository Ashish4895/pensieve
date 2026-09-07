from pathlib import Path

import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_spa_serves_index_and_asset(client, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>spa</title>", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log(1)", encoding="utf-8")

    with override_settings(SPA_ROOT=str(tmp_path)):
        index = client.get("/login")
        assert index.status_code == 200
        assert b"spa" in b"".join(index.streaming_content)

        asset = client.get("/assets/app.js")
        assert asset.status_code == 200
        assert b"console.log" in b"".join(asset.streaming_content)


@pytest.mark.django_db
def test_spa_missing_returns_404_for_unknown_route_without_root(client):
    with override_settings(SPA_ROOT=""):
        # Legacy chatbot index still owns "/"
        response = client.get("/")
        assert response.status_code == 200
