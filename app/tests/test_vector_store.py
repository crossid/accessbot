import os
from unittest import TestCase

from app.embeddings import create_embedding
from app.vector_store import create_org_vstore


class TestVectorStore(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = "/tmp/vss.db"

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.db_file)

    def test_create_org_vstore(self):
        org_id = "acme"
        vs = create_org_vstore(
            org_id,
            uri=f"sqlite://{self.db_file}",
            embedding=create_embedding("sentence_transformer"),
        )
        t1 = "Ketanji Brown Jackson is awesome"
        t2 = "Ketanji Brown Jackson job is a judge"
        vs.add_texts([t1, t2])
        data = vs.similarity_search("what is the role of Ketanji Brown Jackson?")
        self.assertEqual(t1, data[0].page_content)
