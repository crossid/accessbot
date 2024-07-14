from abc import ABC, abstractmethod
from typing import List


class EmailSenderInterface(ABC):
    @abstractmethod
    def send(self, from_addr: str, to: str | List[str], msg: str, subject: str) -> bool:
        pass
