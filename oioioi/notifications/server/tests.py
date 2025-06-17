import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from socketify import OpCode
import aiohttp
import aio_pika

from oioioi.base.tests import TestCase

from oioioi.notifications.server.auth import Auth
from oioioi.notifications.server.queue import Queue
from oioioi.notifications.server.server import Server


@patch('aiohttp.ClientSession')
class AuthTest(TestCase):
    def setUp(self):
        self.auth = Auth('http://example.com/')

    async def test_connect(self, mock_client):
        await self.auth.connect()

        mock_client.assert_called_once()

    async def test_authenticate_without_connect(self, mock_client):
        with self.assertRaisesMessage(RuntimeError, "Connection not established"):
            await self.auth.authenticate("session_id")

    async def test_authenticate_cache_hit(self, mock_client):
        await self.auth.connect()

        self.auth.auth_cache["session_id"] = "user_id"
        result = await self.auth.authenticate("session_id")

        self.assertEqual(result, "user_id")

    async def test_authenticate_successful(self, mock_client):
        await self.auth.connect()

        mock_response = (
            mock_client.return_value.post.return_value.__aenter__.return_value
        )
        mock_response.json.return_value = {"status": "OK", "user": "user_id"}
        mock_response.raise_for_status = MagicMock()

        result = await self.auth.authenticate("session_id")

        self.assertEqual(result, "user_id")
        self.assertEqual(self.auth.auth_cache["session_id"], "user_id")

        mock_client.return_value.post.assert_called_once_with(
            self.auth.auth_url,
            data={'nsid': "session_id"},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )

    async def test_authenticate_error_server_status(self, mock_client):
        await self.auth.connect()

        mock_response = (
            mock_client.return_value.post.return_value.__aenter__.return_value
        )
        mock_response.json.return_value = {"status": "ERROR"}
        mock_response.raise_for_status = Mock()

        with self.assertRaisesMessage(RuntimeError, "Authentication failed"):
            await self.auth.authenticate("session_id")

    async def test_authenticate_error_http_status(self, mock_client):
        await self.auth.connect()

        mock_response = (
            mock_client.return_value.post.return_value.__aenter__.return_value
        )
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientError())

        with self.assertRaises(aiohttp.ClientError):
            await self.auth.authenticate("session_id")


@patch('aio_pika.connect_robust')
class QueueTest(TestCase):
    """Tests for the Queue class."""

    def setUp(self):
        self.message_handler = MagicMock()
        self.queue = Queue('amqp://localhost', self.message_handler)

    async def test_connect(self, mock_connect):
        await self.queue.connect()

        mock_connect.assert_called_once_with(self.queue.amqp_url)

    async def test_subscribe_without_connect(self, mock_connect):
        with self.assertRaisesMessage(RuntimeError, "Connection not established"):
            await self.queue.subscribe("user_id")

    async def test_unsubscribe_without_connect(self, mock_connect):
        with self.assertRaisesMessage(RuntimeError, "Connection not established"):
            await self.queue.unsubscribe("user_id")

    async def test_subscribe(self, mock_connect):
        await self.queue.connect()

        await self.queue.subscribe("user_id")

        declare_queue = mock_connect.return_value.channel.return_value.declare_queue
        declare_queue.assert_called_once_with(
            self.queue.QUEUE_PREFIX + "user_id", durable=True
        )
        declare_queue.return_value.consume.assert_called_once()

    async def test_subscribe_already_subscribed(self, mock_connect):
        await self.queue.connect()

        await self.queue.subscribe("user_id")
        await self.queue.subscribe("user_id")  # should not declare again

        declare_queue = mock_connect.return_value.channel.return_value.declare_queue
        declare_queue.assert_called_once()
        declare_queue.return_value.consume.assert_called_once()

    async def test_unsubscribe(self, mock_connect):
        await self.queue.connect()

        queue = (
            mock_connect.return_value.channel.return_value.declare_queue.return_value
        )
        queue.consume.return_value = "consumer_tag"

        await self.queue.subscribe("user_id")
        await self.queue.unsubscribe("user_id")

        queue.cancel.assert_called_once_with("consumer_tag")

    async def test_message_processing(self, mock_connect):
        await self.queue.connect()
        await self.queue.subscribe("user_id")

        queue = (
            mock_connect.return_value.channel.return_value.declare_queue.return_value
        )
        callback = queue.consume.call_args[0][0]

        mock_message = MagicMock()
        mock_message.body.decode.return_value = "test_message"

        await callback(mock_message)

        self.message_handler.assert_called_once_with("user_id", "test_message")


@patch('oioioi.notifications.server.server.App')
@patch('oioioi.notifications.server.server.Queue', autospec=True)
@patch('oioioi.notifications.server.server.Auth', autospec=True)
class ServerTest(TestCase):
    def setUp(self):
        self.port = 8080
        self.amqp_url = 'amqp://localhost'
        self.auth_url = 'http://example.com'

    def test_initialization(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_app.assert_called_once()
        mock_auth.assert_called_once_with(self.auth_url)
        mock_queue.assert_called_once_with(self.amqp_url, server.on_rabbit_message)

    async def test_on_start(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)

        await server.on_start()

        mock_auth.return_value.connect.assert_called_once()
        mock_queue.return_value.connect.assert_called_once()

    async def test_on_ws_message_unknown(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)
        server.logger = MagicMock()

        mock_ws = MagicMock()
        message = json.dumps({"type": "wrong"})
        await server.on_ws_message(mock_ws, message, OpCode.TEXT)

        server.logger.warning.assert_called_once()

    async def test_on_ws_message_invalid(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)
        server.logger = MagicMock()

        mock_ws = MagicMock()
        message = "Not a valid JSON message"
        await server.on_ws_message(mock_ws, message, OpCode.TEXT)

        server.logger.error.assert_called_once()

    async def test_on_ws_message_auth_success(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_auth.return_value.authenticate.return_value = "user_id"

        mock_ws = MagicMock()
        mock_ws.get_user_data.return_value = {"user_id": None}
        message = json.dumps({"type": "SOCKET_AUTH", "session_id": "session_id"})
        await server.on_ws_message(mock_ws, message, OpCode.TEXT)

        mock_auth.return_value.authenticate.assert_called_once_with("session_id")
        mock_queue.return_value.subscribe.assert_called_once_with("user_id")
        mock_ws.subscribe.assert_called_once_with("user_id")
        mock_ws.send.assert_called_once_with(
            {"type": "SOCKET_AUTH_RESULT", "status": "OK"}, OpCode.TEXT
        )

    async def test_on_ws_message_auth_failure(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_auth.return_value.authenticate.side_effect = RuntimeError(
            "Authentication failed"
        )

        mock_ws = MagicMock()
        mock_ws.get_user_data.return_value = {"user_id": None}
        message = json.dumps({"type": "SOCKET_AUTH", "session_id": "session_id"})
        await server.on_ws_message(mock_ws, message, OpCode.TEXT)

        mock_auth.return_value.authenticate.assert_called_once_with("session_id")
        mock_queue.return_value.subscribe.assert_not_called()
        mock_ws.subscribe.assert_not_called()
        mock_ws.send.assert_called_once_with(
            {"type": "SOCKET_AUTH_RESULT", "status": "ERR_AUTH_FAILED"}, OpCode.TEXT
        )
        
    async def test_on_ws_message_auth_multiple_times(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_ws = MagicMock()
        # Set up the mock websocket to return user data indicating it's already authenticated
        mock_ws.get_user_data.return_value = {"user_id": "user_id"}
        
        message = json.dumps({"type": "SOCKET_AUTH", "session_id": "session_id"})
        await server.on_ws_message(mock_ws, message, OpCode.TEXT)

        # Verify authentication was not attempted again
        mock_auth.return_value.authenticate.assert_not_called()
        mock_queue.return_value.subscribe.assert_not_called()
        mock_ws.subscribe.assert_not_called()
        mock_ws.send.assert_called_once_with(
            {"type": "SOCKET_AUTH_RESULT", "status": "ERR_AUTH_FAILED"}, OpCode.TEXT
        )

    async def test_on_ws_close(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_app.return_value.num_subscribers.return_value = 0

        mock_ws = MagicMock()
        mock_ws.get_user_data.return_value = {"user_id": "user_id"}
        await server.on_ws_close(mock_ws, 0, "")

        mock_queue.return_value.unsubscribe.assert_called_once_with("user_id")

    async def test_on_ws_close_with_other(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)

        # This means that there are still other sockets to this username
        mock_app.return_value.num_subscribers.return_value = 1

        mock_ws = MagicMock()
        mock_ws.get_user_data.return_value = {"user_id": "user_id"}
        await server.on_ws_close(mock_ws, 0, "")

        mock_queue.return_value.unsubscribe.assert_not_called()

    def test_on_rabbit_message(self, mock_auth, mock_queue, mock_app):
        server = Server(self.port, self.amqp_url, self.auth_url)

        server.on_rabbit_message("user_id", "message")

        mock_app.return_value.publish.assert_called_once_with(
            "user_id", "message", OpCode.TEXT
        )
