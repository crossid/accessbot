from typing import List

from sqlalchemy import Engine, text

from .domain import HealthCheckInterface
from .enum import HealthCheckStatusEnum
from .service import HealthCheckBase


class HealthCheckSQL(HealthCheckBase, HealthCheckInterface):
    _tags: List[str]
    _engine: Engine
    _table: str

    def __init__(self, table: str, alias: str, tags: List[str], engine: Engine) -> None:
        self._alias = alias
        self._table = table
        self._tags = tags
        self._engine = engine

    def __checkHealth__(self) -> HealthCheckStatusEnum:
        res: HealthCheckStatusEnum = HealthCheckStatusEnum.UNHEALTHY
        with self._engine.connect() as conn:
            try:
                r = -1
                r = (
                    conn.execute(text(f"SELECT count(*) from {self._table}"))
                    .scalars()
                    .all()
                )
                if r != -1:
                    res = HealthCheckStatusEnum.HEALTHY
            except Exception:
                pass
        return res
