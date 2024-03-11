import asyncio
import unittest
from typing import Any

from app.models import User, Workspace


class TestCreateTicketTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import injector

        from app.injector_extensions_module import ExtensionModule
        from app.services import set_service_registry

        service_registry = injector.Injector([ExtensionModule()])
        set_service_registry(service_registry)

    def test_make_request(self):
        from app.llm.tools.consts import TICKET_SYSTEM_CONFIG_KEY
        from app.llm.tools.create_ticket_for_role_request_tool import make_request

        config: dict[str, Any] = {
            TICKET_SYSTEM_CONFIG_KEY: {"type": "_mock_", "config": {}}
        }

        ws = Workspace(
            display_name="foo", creator_id="bar", config=config, created_by="bar"
        )
        owner = User(id="123", email="john.doe@mock.com")
        output = "making request"

        _ = asyncio.new_event_loop().run_until_complete(
            make_request(
                ws=ws,
                owner=owner,
                output=output,
                requester=owner,
                access=[],
                conv_summary="conv_summary",
                conversation_id="123",
                app_name="foo",
            )
        )

        self.assertEqual(owner.full_name, output)

    def test_extra_fields(self):
        from app.llm.tools.create_ticket_for_role_request_tool import (
            create_expanded_model,
        )

        extra_fields = {"foo": {"description": "my foo"}}

        rtt = create_expanded_model(extra_fields=extra_fields)
        print(rtt)
