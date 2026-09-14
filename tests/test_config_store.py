from __future__ import annotations

import json

from app.graph.config import GraphConfigStore
from app.graph.models import GraphSettings


def test_save_then_load_round_trips_tenant_and_client_id(tmp_path) -> None:
    store = GraphConfigStore(tmp_path / "graph_config.json")
    settings = GraphSettings(tenant_id="tenant-1", client_id="client-1", stale_device_days=14)
    store.save(settings)
    loaded = store.load()
    assert loaded == settings


def test_load_returns_none_when_file_absent(tmp_path) -> None:
    store = GraphConfigStore(tmp_path / "graph_config.json")
    assert store.load() is None


def test_clear_removes_the_file(tmp_path) -> None:
    path = tmp_path / "graph_config.json"
    store = GraphConfigStore(path)
    store.save(GraphSettings(tenant_id="tenant-1", client_id="client-1"))
    assert path.exists()
    store.clear()
    assert not path.exists()


def test_clear_on_missing_file_does_not_raise(tmp_path) -> None:
    store = GraphConfigStore(tmp_path / "graph_config.json")
    store.clear()


def test_saved_file_contains_only_non_sensitive_fields(tmp_path) -> None:
    path = tmp_path / "graph_config.json"
    store = GraphConfigStore(path)
    store.save(GraphSettings(tenant_id="tenant-1", client_id="client-1", stale_device_days=7))
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert set(payload.keys()) == {"tenant_id", "client_id", "stale_device_days"}
    assert "secret" not in raw.lower()


def test_config_dir_resolves_via_central_user_data_dir_helper() -> None:
    from app.core.paths import user_data_dir
    from app.graph.config import CONFIG_DIR

    assert CONFIG_DIR == user_data_dir()
