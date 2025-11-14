"""replace difficulty enum with string

Revision ID: 1ef127d8a9b4
Revises: 0001_create_scene_tables
Create Date: 2025-11-13 16:44:49.238168
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "1ef127d8a9b4"
down_revision = "0001_create_scene_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE scene ALTER COLUMN difficulty TYPE VARCHAR(16) USING difficulty::text"
    )
    op.execute(
        "ALTER TABLE scene ALTER COLUMN table_variant TYPE VARCHAR(32) USING table_variant::text"
    )

    op.execute(
        "ALTER TABLE trajectory_segment ALTER COLUMN ball_name TYPE VARCHAR(16) USING ball_name::text"
    )
    op.execute(
        "ALTER TABLE ball_position ALTER COLUMN ball_name TYPE VARCHAR(16) USING ball_name::text"
    )

    op.execute(
        "ALTER TABLE cue_parameters ALTER COLUMN effect_stage TYPE VARCHAR(32) USING effect_stage::text"
    )
    op.execute(
        "ALTER TABLE cue_parameters ALTER COLUMN effect_side TYPE VARCHAR(16) USING effect_side::text"
    )
    op.execute("ALTER TABLE cue_parameters ALTER COLUMN effect_side SET DEFAULT 'none'")

    for enum_name in [
        "difficulty",
        "tablevariant",
        "ballname",
        "effectstage",
        "effectside",
    ]:
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))


def downgrade() -> None:
    op.execute(
        "CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard')"
    )
    op.execute(
        "ALTER TABLE scene ALTER COLUMN difficulty TYPE difficulty USING difficulty::difficulty"
    )

    op.execute(
        "CREATE TYPE tablevariant AS ENUM ('match', 'small_tournament')"
    )
    op.execute(
        "ALTER TABLE scene ALTER COLUMN table_variant TYPE tablevariant USING table_variant::tablevariant"
    )

    op.execute(
        "CREATE TYPE ballname AS ENUM ('B1', 'B2', 'B3', 'GHOST')"
    )
    op.execute(
        "ALTER TABLE trajectory_segment ALTER COLUMN ball_name TYPE ballname USING ball_name::ballname"
    )
    op.execute(
        "ALTER TABLE ball_position ALTER COLUMN ball_name TYPE ballname USING ball_name::ballname"
    )

    op.execute(
        "CREATE TYPE effectstage AS ENUM ('stage_0', 'stage_1', 'stage_2', 'stage_3', 'stage_4', 'stage_45_deg', 'stage_4_plus')"
    )
    op.execute(
        "ALTER TABLE cue_parameters ALTER COLUMN effect_stage TYPE effectstage USING effect_stage::effectstage"
    )

    op.execute(
        "CREATE TYPE effectside AS ENUM ('none', 'left', 'right')"
    )
    op.execute(
        "ALTER TABLE cue_parameters ALTER COLUMN effect_side TYPE effectside USING effect_side::effectside"
    )
    op.execute(
        "ALTER TABLE cue_parameters ALTER COLUMN effect_side SET DEFAULT 'none'::effectside"
    )

