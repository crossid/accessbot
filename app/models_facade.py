from abc import ABC, abstractmethod
from logging import Logger
from typing import Optional

from app.models import Org


class OrgFacade(ABC):
    @property
    def logger(self) -> Logger:
        raise NotImplementedError()

    @abstractmethod
    def get_by_id(self, org_id: str) -> Optional[Org]:
        pass

    @abstractmethod
    def insert(self, org: Org) -> Org:
        pass


class OrgFacadeHooks(ABC):
    @abstractmethod
    def pre_insert(self, org: Org):
        pass


class OrgFacadeProxy:
    def __init__(self, facade: OrgFacade, hooks: OrgFacadeHooks):
        self._facade = facade
        self._hooks = hooks

    def get_by_id(self, org_id: str) -> Optional[Org]:
        return self._facade.get_by_id(org_id)

    def insert(self, org: Org) -> Org:
        if self._hooks:
            self._hooks.pre_insert(org)
        return self._facade.insert(org)
