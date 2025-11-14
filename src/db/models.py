from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Difficulty(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TableVariant(enum.Enum):
    MATCH = "match"
    SMALL_TOURNAMENT = "small_tournament"


class BallName(enum.StrEnum):
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    GHOST = "GHOST"


class EffectSide(enum.Enum):
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"


class EffectStage(enum.Enum):
    STAGE_0 = "stage_0"
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"
    STAGE_3 = "stage_3"
    STAGE_4 = "stage_4"
    STAGE_45_DEG = "stage_45_deg"
    STAGE_4_PLUS = "stage_4_plus"


class Scene(Base):
    __tablename__ = "scene"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scene_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text())
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)

    source_work: Mapped[str] = mapped_column(String(200), nullable=False)
    source_section: Mapped[Optional[str]] = mapped_column(String(200))
    source_page: Mapped[Optional[int]] = mapped_column(Integer())

    table_variant: Mapped[str] = mapped_column(String(32), nullable=False)
    table_width_units: Mapped[float] = mapped_column(nullable=False)
    table_height_units: Mapped[float] = mapped_column(nullable=False)
    grid_resolution: Mapped[float] = mapped_column(nullable=False)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"), onupdate=datetime.utcnow
    )

    ball_positions: Mapped[list[BallPosition]] = relationship(back_populates="scene", cascade="all, delete-orphan")
    cue_parameters: Mapped[Optional[CueParameters]] = relationship(
        back_populates="scene", cascade="all, delete-orphan", uselist=False
    )
    tempo_force: Mapped[Optional[TempoForce]] = relationship(
        back_populates="scene", cascade="all, delete-orphan", uselist=False
    )
    trajectory_segments: Mapped[list[TrajectorySegment]] = relationship(
        back_populates="scene", cascade="all, delete-orphan", order_by="TrajectorySegment.sequence_index"
    )
    notes: Mapped[list[SceneNote]] = relationship(back_populates="scene", cascade="all, delete-orphan")
    sources: Mapped[list[SceneSourceAsset]] = relationship(back_populates="scene", cascade="all, delete-orphan")


class BallPosition(Base):
    __tablename__ = "ball_position"
    __table_args__ = (
        UniqueConstraint("scene_id", "ball_name", name="uq_ball_position_scene_ball"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[UUID] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"), nullable=False)
    ball_name: Mapped[str] = mapped_column(String(16), nullable=False)
    color: Mapped[str] = mapped_column(String(32), nullable=False)
    x: Mapped[float] = mapped_column(nullable=False)
    y: Mapped[float] = mapped_column(nullable=False)
    is_ghost: Mapped[bool] = mapped_column(default=False, nullable=False)

    scene: Mapped[Scene] = relationship(back_populates="ball_positions")


class CueParameters(Base):
    __tablename__ = "cue_parameters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[UUID] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"), unique=True)
    attack_height: Mapped[Optional[str]] = mapped_column(String(50))
    effect_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    effect_side: Mapped[str] = mapped_column(String(16), nullable=False, default=EffectSide.NONE.value)
    cue_inclination_deg: Mapped[Optional[float]] = mapped_column()
    notes: Mapped[Optional[str]] = mapped_column(Text())

    scene: Mapped[Scene] = relationship(back_populates="cue_parameters")


class TempoForce(Base):
    __tablename__ = "tempo_force"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[UUID] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"), unique=True)
    tempo: Mapped[int] = mapped_column(Integer(), CheckConstraint("tempo BETWEEN 0 AND 5"), nullable=False)
    force: Mapped[int] = mapped_column(Integer(), CheckConstraint("force BETWEEN 0 AND 5"), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text())

    scene: Mapped[Scene] = relationship(back_populates="tempo_force")


class TrajectorySegment(Base):
    __tablename__ = "trajectory_segment"
    __table_args__ = (
        CheckConstraint("sequence_index >= 0", name="ck_segment_sequence_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[UUID] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"), nullable=False)
    ball_name: Mapped[str] = mapped_column(String(16), nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    path_type: Mapped[str] = mapped_column(String(16), nullable=False, default="line")
    point_x: Mapped[float] = mapped_column(nullable=False)
    point_y: Mapped[float] = mapped_column(nullable=False)
    event_kind: Mapped[Optional[str]] = mapped_column(String(64))
    notes: Mapped[Optional[str]] = mapped_column(Text())

    scene: Mapped[Scene] = relationship(back_populates="trajectory_segments")


class SceneNote(Base):
    __tablename__ = "scene_note"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[UUID] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)

    scene: Mapped[Scene] = relationship(back_populates="notes")


class SceneSourceAsset(Base):
    __tablename__ = "scene_source_asset"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[UUID] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    uri: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text())

    scene: Mapped[Scene] = relationship(back_populates="sources")
