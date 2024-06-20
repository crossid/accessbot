from typing import List

from app.data_fetching.iface import DataFetcherInterface
from app.data_fetching.utils import Doc


class DFMockImpl(DataFetcherInterface):
    async def fetch_content() -> List[Doc]:
        return []
