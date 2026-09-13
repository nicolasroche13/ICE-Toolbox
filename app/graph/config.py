from __future__ import annotations

import json
from pathlib import Path

from app.graph.models import GraphSettings


CONFIG_DIR = Path.home() / ".endpoint_toolbox"
GRAPH_CONFIG_FILE = CONFIG_DIR / "graph_config.json"


class GraphConfigStore:
    def __init__(self, path: Path = GRAPH_CONFIG_FILE):
        self.path = path

    def load(self) -> GraphSettings | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        tenant_id = str(data.get("tenant_id", "")).strip()
        client_id = str(data.get("client_id", "")).strip()
        stale_device_days = int(data.get("stale_device_days", 7))
        if not tenant_id or not client_id:
            return None
        return GraphSettings(tenant_id=tenant_id, client_id=client_id, stale_device_days=stale_device_days)

    def save(self, settings: GraphSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tenant_id": settings.tenant_id.strip(),
            "client_id": settings.client_id.strip(),
            "stale_device_days": settings.stale_device_days,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

