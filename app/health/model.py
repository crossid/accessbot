from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel

from .enum import HealthCheckStatusEnum


class HealthCheckEntityModel(BaseModel):
    alias: str
    status: Union[HealthCheckStatusEnum, str] = HealthCheckStatusEnum.HEALTHY
    timeTaken: Union[Optional[datetime], str] = ""
    tags: List[str] = list()


class HealthCheckModel(BaseModel):
    status: Union[HealthCheckStatusEnum, str] = HealthCheckStatusEnum.HEALTHY
    duration: Union[Optional[datetime], str] = ""
    entities: List[HealthCheckEntityModel] = list()
