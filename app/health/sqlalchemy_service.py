from typing import List

from sqlalchemy import text
from sqlmodel import Session

from .domain import HealthCheckInterface
from .enum import HealthCheckStatusEnum
from .service import HealthCheckBase


class HealthCheckSQL(HealthCheckBase, HealthCheckInterface):
    _tags: List[str]
    _session: Session
    _table: str

    def __init__(
        self, table: str, alias: str, tags: List[str], session: Session
    ) -> None:
        self._alias = alias
        self._table = table
        self._tags = tags
        self._session = session

    def __checkHealth__(self) -> HealthCheckStatusEnum:
        res: HealthCheckStatusEnum = HealthCheckStatusEnum.UNHEALTHY
        with self._session:
            try:
                r = -1
                r = (
                    self._session.exec(text(f"SELECT count(*) from {self._table}"))
                    .scalars()
                    .all()
                )
                if r != -1:
                    res = HealthCheckStatusEnum.HEALTHY
            except Exception:
                pass
        return res
