from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field, validator

from src.db.models import (
    BallName,
    Difficulty,
    EffectSide,
    EffectStage,
    TableVariant,
    TrajectoryType,
)


class SourceModel(BaseModel):
    work: str
    section: str | None = None
    page: int | None = Field(default=None, ge=0)


class TableModel(BaseModel):
    type: Literal["carom_standard"]
    size_units: List[float]
    unit: str
    origin: str
    grid_resolution: float
    physical_size_cm: List[float] | None = None
    variant: TableVariant

    @validator("size_units")
    def validate_size_units(cls, value: List[float]) -> List[float]:
        if len(value) != 2:
            raise ValueError("size_units must have two values [width, height]")
        return value


class BallPositionModel(BaseModel):
    color: str
    position: List[float]

    @validator("position")
    def validate_position(cls, value: List[float]) -> List[float]:
        if len(value) != 2:
            raise ValueError("Ball position must contain [x, y]")
        return value


class GhostBallModel(BaseModel):
    position: List[float]
    notes: str | None = None


class BallContactModel(BaseModel):
    fraction: float
    label: str


class CueModel(BaseModel):
    cue_direction: List[float]
    attack_height: str | None = None
    effect_stage: EffectStage = EffectStage.STAGE_0
    effect_side: EffectSide = EffectSide.NONE
    cue_inclination_deg: float | None = None
    notes: List[str] | None = None

    @validator("cue_direction")
    def validate_direction(cls, value: List[float]) -> List[float]:
        if len(value) != 2:
            raise ValueError("cue_direction must have two components [x, y]")
        return value


class TempoForceModel(BaseModel):
    tempo: int = Field(ge=0, le=5)
    force: int = Field(ge=0, le=5)
    comments: str | None = None


class TrajectorySegmentModel(BaseModel):
    type: TrajectoryType
    to: List[float] | None = None
    position: List[float] | None = None
    cushion: str | None = None
    notes: str | None = None


class TextBlockModel(BaseModel):
    original_language: str
    original_excerpt: str
    de_summary: str | None = None


class SceneModel(BaseModel):
    id: str
    title: str
    source: SourceModel
    difficulty: Difficulty
    description: str | None = None
    table: TableModel
    balls: Dict[str, BallPositionModel]
    ghost_ball: GhostBallModel | None = None
    ball_contact: BallContactModel | None = None
    cue: CueModel | None = None
    tempo_force: TempoForceModel | None = None
    trajectory: Dict[str, List[TrajectorySegmentModel]] = Field(default_factory=dict)
    text: TextBlockModel | None = None
    remarks: List[str] = Field(default_factory=list)

    def require_ball(self, ball: BallName) -> BallPositionModel:
        key = ball.value
        if key not in self.balls:
            raise KeyError(f"Scene {self.id} is missing ball {key}")
        return self.balls[key]
