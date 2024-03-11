import asyncio
import unittest
from typing import Any

from langchain_core.messages import HumanMessage

from app.llm.graph import CONVERSATION_TYPE_KEY
from app.llm.prompts import (
    CONVERSATION_ID_KEY,
    MEMORY_KEY,
    USER_EMAIL_KEY,
    WS_ID_KEY,
)
from app.models import Conversation, ConversationTypes, User, Workspace


class TestGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import injector

        from app.injector_extensions_module import ExtensionModule
        from app.services import set_service_registry

        service_registry = injector.Injector([ExtensionModule()])
        set_service_registry(service_registry)

    def test_make_request(self):
        from dotenv import load_dotenv

        from app.llm.conversation import create_agent_for_access_request_conversation
        from app.llm.tools.consts import TICKET_SYSTEM_CONFIG_KEY

        load_dotenv()

        config: dict[str, Any] = {
            TICKET_SYSTEM_CONFIG_KEY: {"type": "_mock_", "config": {}}
        }

        ws = Workspace(
            id="IDro10K0ux", display_name="foo", created_by="bar", config=config
        )
        conversation = Conversation(
            id="1",
            workspace_id="IDro10K0ux",
            created_by="bar",
            context={},
            type=ConversationTypes.recommendation,
        )
        user = User(id="123", email="john.doe@mock.com")
        data_context = {
            USER_EMAIL_KEY: user.email,
            WS_ID_KEY: conversation.workspace_id,
            CONVERSATION_ID_KEY: conversation.id,
        }

        graph = create_agent_for_access_request_conversation(
            conversation=conversation, ws=ws, data_context=data_context
        )

        result = asyncio.new_event_loop().run_until_complete(
            graph.ainvoke(
                {
                    MEMORY_KEY: [
                        HumanMessage(content="Hello, I need access to fooquery app")
                    ],
                    CONVERSATION_TYPE_KEY: conversation.type.value,
                }
            )
        )

        last_message = result[MEMORY_KEY][-1]
        self.assertTrue(last_message.name == "Information")
        self.assertTrue("fooquery" in last_message.content)
