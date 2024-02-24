from abc import ABC, abstractmethod


class TransactionContext(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def rollback(self):
        pass
