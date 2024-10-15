from abc import ABC, abstractmethod
from typing import List


class EmailSenderInterface(ABC):
    @abstractmethod
    def send(
        self, from_addr: str, to: str | List[str], content: str, subject: str
    ) -> bool:
        pass
