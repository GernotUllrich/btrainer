"""create scene tables

Revision ID: 0001_create_scene_tables
Revises: 
Create Date: 2025-03-09 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_create_scene_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scene",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scene_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("source_work", sa.String(length=200), nullable=False),
        sa.Column("source_section", sa.String(length=200), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("table_variant", sa.String(length=32), nullable=False),
        sa.Column("table_width_units", sa.Float(), nullable=False),
        sa.Column("table_height_units", sa.Float(), nullable=False),
        sa.Column("grid_resolution", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "ball_position",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ball_name", sa.String(length=16), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("is_ghost", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.UniqueConstraint("scene_id", "ball_name", name="uq_ball_position_scene_ball"),
    )

    op.create_table(
        "cue_parameters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attack_height", sa.String(length=50), nullable=True),
        sa.Column("effect_stage", sa.String(length=32), nullable=False),
        sa.Column("effect_side", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("cue_inclination_deg", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("scene_id", name="uq_cue_parameters_scene"),
    )

    op.create_table(
        "tempo_force",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tempo", sa.Integer(), nullable=False),
        sa.Column("force", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.CheckConstraint("tempo BETWEEN 0 AND 5", name="ck_tempo_bounds"),
        sa.CheckConstraint("force BETWEEN 0 AND 5", name="ck_force_bounds"),
        sa.UniqueConstraint("scene_id", name="uq_tempo_force_scene"),
    )

    op.create_table(
        "trajectory_segment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ball_name", sa.String(length=16), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("path_type", sa.String(length=16), nullable=False, server_default="line"),
        sa.Column("point_x", sa.Float(), nullable=False),
        sa.Column("point_y", sa.Float(), nullable=False),
        sa.Column("event_kind", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("sequence_index >= 0", name="ck_segment_sequence_nonnegative"),
    )

    op.create_index(
        "ix_trajectory_scene_sequence",
        "trajectory_segment",
        ["scene_id", "sequence_index"],
    )

    op.create_table(
        "scene_note",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    )

    op.create_table(
        "scene_source_asset",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("uri", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scene_source_asset")
    op.drop_table("scene_note")
    op.drop_index("ix_trajectory_scene_sequence", table_name="trajectory_segment")
    op.drop_table("trajectory_segment")
    op.drop_table("tempo_force")
    op.drop_table("cue_parameters")
    op.drop_table("ball_position")
    op.drop_table("scene")
