import os

import pytest

from app.embeddings import create_embedding
from app.vector_store import create_workspace_vstore


@pytest.fixture(scope="class")
def setup_teardown(request):
    db_file = "/tmp/vss.db"
    request.cls.db_file = db_file  # Set db_file as a class attribute
    yield
    os.remove(db_file)


@pytest.mark.usefixtures("setup_teardown")
class TestVectorStore:
    def test_create_workspace_vstore(self):
        workspace_id = "acme"
        workspace_name = "acme"
        vs = create_workspace_vstore(
            workspace_id=workspace_id,
            uri=f"sqlite://{self.db_file}",
            embedding=create_embedding("sentence_transformer"),
            workspace_name=workspace_name,
        )
        t1 = "Ketanji Brown Jackson is awesome"
        t2 = "Ketanji Brown Jackson job is a judge"
        vs.add_texts([t1, t2])
        data = vs.similarity_search("what is the role of Ketanji Brown Jackson?")
        assert (
            t1 == data[0].page_content
        ), "The top search result should match the first text added"
