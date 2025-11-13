from __future__ import annotations

from pathlib import Path

from src.db.schemas import SceneModel


def test_yaml_scene_loads() -> None:
    path = Path("data/annotations/gretillat/VS-Lang-02-01.yaml")
    import yaml
    raw = yaml.safe_load(path.read_text())
    data = SceneModel.model_validate(raw["scene"])
    assert data.id == "VS-Lang-02-01"
    assert "B1" in data.balls
