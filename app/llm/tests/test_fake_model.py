import unittest

from app.llm.fake_model import FakeChatOpenAI
from app.llm.model import create_model


class TestParseModelURI(unittest.TestCase):
    def test_parse_model_uri(self):
        from app.llm.model import get_model_from_uri

        uri = "openai://gpt-3.5?temperature=0.9&streaming=true"
        model, name, qp = get_model_from_uri(uri)
        self.assertEqual(model, "openai")
        self.assertEqual(name, "gpt-3.5")
        self.assertEqual(qp, {"temperature": ["0.9"], "streaming": ["true"]})

        uri = "fake://test"
        model, name, qp = get_model_from_uri(uri)
        self.assertEqual(model, "fake")
        self.assertEqual(name, "test")
        self.assertEqual(qp, {})


class TestFakeModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.settings import settings

        settings.LLM_MODEL = "fake://"

    def test_fake_model_type(self):
        model = create_model(responses=[])
        self.assertIsInstance(model, FakeChatOpenAI)

    def test_fake_model_invoke(self):
        model = create_model(responses=["foo bar"])
        result = model.invoke(input="hello1")
        self.assertEqual(result.content, "foo bar")

    def test_fake_model_streaming(self):
        model = create_model(responses=["foo bar"])
        content = ""
        for chunk in model.stream(input="hello"):
            content += chunk.content
        self.assertEqual(content, "foo bar")
