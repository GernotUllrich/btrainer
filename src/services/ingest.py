from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml
from sqlalchemy.orm import Session

from sqlalchemy.orm import object_session

from src.db import models
from src.db.schemas import SceneModel




def _replace_todo(value):
    if isinstance(value, dict):
        return {k: _replace_todo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_todo(v) for v in value]
    if isinstance(value, str) and value.strip().upper() == "TODO":
        return 0.0
    return value

def load_scene_yaml(path: Path) -> SceneModel:
    with path.open() as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict) or "scene" not in raw:
        raise ValueError(f"YAML file {path} does not contain a 'scene' root object")
    cleaned = _replace_todo(raw["scene"])
    return SceneModel.model_validate(cleaned)


def upsert_scene(session: Session, scene_data: SceneModel) -> models.Scene:
    scene = (
        session.query(models.Scene)
        .filter(models.Scene.scene_key == scene_data.id)
        .one_or_none()
    )
    if scene is None:
        scene = models.Scene(scene_key=scene_data.id)
        session.add(scene)

    scene.title = scene_data.title
    scene.description = scene_data.description
    scene.difficulty = scene_data.difficulty.value
    scene.source_work = scene_data.source.work
    scene.source_section = scene_data.source.section
    # Extrahiere Seitennummer (kann String wie "270 oben" sein)
    if scene_data.source.page is not None:
        if isinstance(scene_data.source.page, int):
            scene.source_page = scene_data.source.page
        else:
            # Extrahiere Zahl aus String
            import re
            match = re.search(r'\d+', str(scene_data.source.page))
            scene.source_page = int(match.group()) if match else None
    else:
        scene.source_page = None

    scene.table_variant = scene_data.table.variant.value
    scene.table_width_units = scene_data.table.size_units[0]
    scene.table_height_units = scene_data.table.size_units[1]
    scene.grid_resolution = scene_data.table.grid_resolution
    metadata = {"table": scene_data.table.model_dump(mode="json")}
    if scene_data.text:
        metadata["text"] = scene_data.text.model_dump(mode="json")
    scene.metadata_json = metadata

    session_ref = object_session(scene)

    scene.ball_positions.clear()
    if session_ref is not None:
        session_ref.flush()
    for name, payload in scene_data.balls.items():
        x, y = payload.position
        scene.ball_positions.append(
            models.BallPosition(
                ball_name=name,
                color=payload.color,
                x=x,
                y=y,
                is_ghost=False,
            )
        )

    if scene_data.ghost_ball:
        gx, gy = scene_data.ghost_ball.position
        scene.ball_positions.append(
            models.BallPosition(
                ball_name=models.BallName.GHOST.value,
                color="ghost",
                x=gx,
                y=gy,
                is_ghost=True,
            )
        )

    if scene_data.cue:
        if scene.cue_parameters is None:
            scene.cue_parameters = models.CueParameters()
        scene.cue_parameters.attack_height = scene_data.cue.attack_height
        scene.cue_parameters.effect_stage = scene_data.cue.effect_stage.value
        scene.cue_parameters.effect_side = scene_data.cue.effect_side.value
        scene.cue_parameters.cue_inclination_deg = scene_data.cue.cue_inclination_deg
        scene.cue_parameters.notes = "\n".join(scene_data.cue.notes or []) or None
    else:
        scene.cue_parameters = None

    if scene_data.tempo_force:
        if scene.tempo_force is None:
            scene.tempo_force = models.TempoForce()
        scene.tempo_force.tempo = scene_data.tempo_force.tempo
        scene.tempo_force.force = scene_data.tempo_force.force
        scene.tempo_force.comments = scene_data.tempo_force.comments
    else:
        scene.tempo_force = None

    scene.trajectory_segments.clear()
    for ball_key, segments in scene_data.trajectory.items():
        for index, segment in enumerate(segments):
            px, py = segment.point
            scene.trajectory_segments.append(
                models.TrajectorySegment(
                    ball_name=getattr(ball_key, "value", ball_key),
                    sequence_index=index,
                    path_type=segment.path_type,
                    point_x=px,
                    point_y=py,
                    event_kind=segment.event,
                    notes=segment.notes,
                )
            )

    scene.notes.clear()
    scene.notes.extend(models.SceneNote(content=remark) for remark in scene_data.remarks)

    if scene_data.text:
        text_note = f"{scene_data.text.original_language}: {scene_data.text.original_excerpt.strip()}"
        scene.notes.append(models.SceneNote(content=text_note))
        if scene_data.text.de_summary:
            scene.notes.append(models.SceneNote(content=f"de_summary: {scene_data.text.de_summary.strip()}"))

    scene.sources.clear()
    scene.sources.append(
        models.SceneSourceAsset(
            asset_type="image",
            uri=str(Path("data/raw/gretillat") / f"{scene_data.id}.png"),
            description=scene_data.source.section,
        )
    )

    return scene


def import_scenes(session: Session, scene_paths: Iterable[Path]) -> list[models.Scene]:
    imported: list[models.Scene] = []
    for path in scene_paths:
        scene_model = load_scene_yaml(path)
        scene = upsert_scene(session, scene_model)
        imported.append(scene)
    session.flush()
    return imported
