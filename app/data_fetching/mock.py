from typing import List

from app.data_fetching.iface import DataFetcherInterface
from app.data_fetching.utils import Doc


class DFMockImpl(DataFetcherInterface):
    async def fetch_content(dir_name: str, **kwargs) -> List[Doc]:
        return []
