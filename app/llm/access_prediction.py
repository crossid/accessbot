from collections import Counter
from typing import Any

from app.embeddings import create_embedding
from app.models import Application, Workspace
from app.settings import settings
from app.vector_store import create_workspace_vstore


def calculate_access_density(data: dict[str, list[str]]):
    # Flatten all sentences into a single list
    all_access = [access for user_access in data.values() for access in user_access]

    # Count occurrences of each sentence
    access_counts = Counter(all_access)

    # Calculate total number of users
    total_users = len(data)

    # Calculate density for each sentence
    access_density = {
        access: count / total_users for access, count in access_counts.items()
    }

    return access_density


def dict_to_md(data: dict[str, Any]) -> str:
    md_lines = []
    for key, value in data.items():
        md_lines.append(f"**{key}**: {value}")
    return "\n".join(md_lines)


async def predict_access_to_user(
    user: dict[str, Any],
    ws: Workspace,
    app: Application,
    top_k: int = 10,
    min_relevance: float = 0.7,
) -> str:
    wvstore = create_workspace_vstore(
        workspace_id=ws.id,
        embedding=create_embedding(settings.VSTORE_EMBEDDING),
        workspace_name=ws.name,
    )
    pass
    # ret = vstore.as_retriever(
    # search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.75}
    # )
