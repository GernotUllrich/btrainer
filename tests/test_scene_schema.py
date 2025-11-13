
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.db.schemas import SceneModel


def _replace_todo(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _replace_todo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_todo(v) for v in value]
    if isinstance(value, str) and value.strip().upper() == "TODO":
        return 0.0
    return value


def test_yaml_scene_loads() -> None:
    path = Path("data/annotations/gretillat/VS-Lang-02-01.yaml")
    raw = yaml.safe_load(path.read_text())
    cleaned = _replace_todo(raw["scene"])
    data = SceneModel.model_validate(cleaned)
    assert data.id == "VS-Lang-02-01"
    assert "B1" in data.balls
