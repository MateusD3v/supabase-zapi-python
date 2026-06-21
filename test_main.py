import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

import main


class FetchContactsTests(unittest.TestCase):
    def test_caps_query_at_three_contacts(self):
        query = Mock()
        query.select.return_value = query
        query.limit.return_value = query
        query.execute.return_value = SimpleNamespace(data=[])

        supabase = Mock()
        supabase.table.return_value = query

        contacts = main.fetch_contacts(supabase, limit=10)

        self.assertEqual(contacts, [])
        supabase.table.assert_called_once_with("contatos")
        query.select.assert_called_once_with("nome, telefone")
        query.limit.assert_called_once_with(3)


class SendMessageTests(unittest.TestCase):
    @patch.object(main, "ZAPI_INSTANCE_ID", "instance-id")
    @patch.object(main, "ZAPI_TOKEN", "instance-token")
    @patch.object(main, "ZAPI_CLIENT_TOKEN", "client-token")
    @patch("main.requests.post")
    def test_sends_exact_personalized_message(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        post.return_value = response

        sent = main.send_zapi_message("5511999999999", "Mateus")

        self.assertTrue(sent)
        post.assert_called_once_with(
            "https://api.z-api.io/instances/instance-id/token/instance-token/send-text",
            json={
                "phone": "5511999999999",
                "message": "Olá, Mateus tudo bem com você?",
            },
            headers={
                "Content-Type": "application/json",
                "Client-Token": "client-token",
            },
            timeout=15,
        )

    @patch.object(main, "ZAPI_INSTANCE_ID", "instance-id")
    @patch.object(main, "ZAPI_TOKEN", "instance-token")
    @patch("main.requests.post", side_effect=requests.ConnectionError("offline"))
    def test_handles_failure_before_response_exists(self, post):
        self.assertFalse(main.send_zapi_message("5511999999999", "Mateus"))
        post.assert_called_once()


class MainTests(unittest.TestCase):
    @patch("main.send_zapi_message", return_value=True)
    @patch("main.fetch_contacts")
    @patch("main.get_supabase_client")
    def test_processes_one_contact_successfully(self, get_client, fetch, send):
        get_client.return_value = Mock()
        fetch.return_value = [{"nome": "Ana", "telefone": "5511999999999"}]

        exit_code = main.main()

        self.assertEqual(exit_code, 0)
        send.assert_called_once_with("5511999999999", "Ana")

    @patch("main.send_zapi_message", return_value=False)
    @patch("main.fetch_contacts")
    @patch("main.get_supabase_client")
    def test_returns_failure_when_a_send_fails(self, get_client, fetch, send):
        get_client.return_value = Mock()
        fetch.return_value = [{"nome": "Ana", "telefone": "5511999999999"}]

        self.assertEqual(main.main(), 1)
        send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
