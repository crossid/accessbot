import asyncio
import unittest
import unittest.mock
from unittest.mock import patch

from app.llm.tools.access_data.webhook import WebhookImpl as ADWI
from app.llm.tools.provision.webhook import WebhookImpl
from app.llm.tools.user_data.webhook import WebhookImpl as UDWI


class TestCreateTicketTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @patch("requests.post")
    def test_provision_webhook(self, mock_post):
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        url = "http://example.com/api"
        expected_body = {"requester_email": "jon.doe@foo.com", "foo": "bar"}
        whi = WebhookImpl(url=url)
        ack = asyncio.run(whi.approve_request(**expected_body))

        self.assertTrue(ack)
        mock_post.assert_called_once_with(url=url, json=expected_body)

    @patch("requests.post")
    def test_access_data_webhook(self, mock_post):
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        expected_text = (
            '{"sensitivity": 5, "description": "grants read and write access"}'
        )

        mock_response.text = expected_text
        mock_post.return_value = mock_response

        url = "http://example.com/api"
        type_mapping = {"access_data_url": "/roles"}
        whi = ADWI(url=url, type_mappings=type_mapping)

        expected_body = {"app_name": "foo"}
        ack = asyncio.run(whi.get_access_data(**expected_body))

        self.assertTrue(ack)

        expected_url = f"{url}/roles"
        mock_post.assert_called_once_with(url=expected_url, json=expected_body)

        actual_response_body = mock_post.return_value.text
        self.assertEqual(actual_response_body, expected_text)

    @patch("requests.post")
    def test_user_data_webhook(self, mock_post):
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        expected_text = '{"email": "jon.doe@vandelay.com"}'

        mock_response.text = expected_text
        mock_post.return_value = mock_response

        url = "http://example.com/api"
        type_mapping = {"user_data_url": "/users"}
        whi = UDWI(url=url, type_mappings=type_mapping)

        args = {"user_email": "jon.doe@vandelay.com"}
        ack = asyncio.run(whi.get_user_data(**args))

        self.assertTrue(ack)

        expected_url = f"{url}/users"
        expected_body = {"email": "jon.doe@vandelay.com"}
        mock_post.assert_called_once_with(url=expected_url, json=expected_body)

        actual_response_body = mock_post.return_value.text
        self.assertEqual(actual_response_body, expected_text)
