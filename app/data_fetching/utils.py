from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.id import generate


class Doc(BaseModel):
    id: Optional[str] = None
    display_name: Optional[str] = None
    apps: Optional[list[str]]
    directory: Optional[str]
    content: Optional[str]
    external_id: Optional[str]


def prepare_metadata_ids_content(docs: List[Doc]):
    metadatas = []
    ids = []
    content = []

    for doc in docs:
        dmeta = {
            "directory": doc.directory,
            "app": doc.apps,
            "created_at": datetime.now().isoformat(),
            "display_name": doc.display_name or "",
        }
        metadatas.append(dmeta)
        ids.append(doc.external_id if doc.external_id is not None else generate())
        content.append(doc.content)

    return content, metadatas, ids
