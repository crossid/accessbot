from abc import ABC, abstractmethod
from typing import List

from app.data_fetching.utils import Doc


class DataFetcherInterface(ABC):
    @abstractmethod
    async def fetch_content(dir_name: str) -> List[Doc]:
        pass
