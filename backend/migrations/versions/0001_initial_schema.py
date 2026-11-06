"""Initial schema migration for assessments and challenges (Appendix B.5, P5-08)."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db import Base

revision: str = "0001_initial_schema"
down_revision: str | None = None


def upgrade(engine: Engine) -> None:
    """Create assessments and challenges tables and indexes."""
    Base.metadata.create_all(bind=engine)


def downgrade(engine: Engine) -> None:
    """Drop challenges and assessments tables."""
    Base.metadata.drop_all(bind=engine)

