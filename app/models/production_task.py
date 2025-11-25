import sqlalchemy as sa

from .base import BaseModel as Base


class ProductionTask(Base):
    """ProductionTask model representing production tasks."""

    __tablename__ = "production_tasks"

    task_name = sa.Column(sa.String)
    run_count = sa.Column(sa.Numeric, default=1)
    max_runs = sa.Column(sa.Numeric, default=1)
