import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp

from oioioi.base.tests import TestCase
from oioioi.notifications.server.auth import Auth
from oioioi.notifications.server.queue import Queue
from oioioi.notifications.server.server import Server, UserConnection


@patch("aiohttp.ClientSession")
class AuthTest(TestCase):
    def setUp(self):
        self.auth = Auth("http://example.com/")

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

        mock_response = mock_client.return_value.post.return_value.__aenter__.return_value
        mock_response.json.return_value = {"user": "user_id"}
        mock_response.raise_for_status = MagicMock()

        result = await self.auth.authenticate("session_id")

        self.assertEqual(result, "user_id")
        self.assertEqual(self.auth.auth_cache["session_id"], "user_id")

        mock_client.return_value.post.assert_called_once_with(
            self.auth.auth_url,
            data={"nsid": "session_id"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def test_authenticate_error(self, mock_client):
        await self.auth.connect()

        mock_response = mock_client.return_value.post.return_value.__aenter__.return_value
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientError())

        with self.assertRaises(aiohttp.ClientError):
            await self.auth.authenticate("session_id")


@patch("aio_pika.connect_robust")
class QueueTest(TestCase):
    """Tests for the Queue class."""

    def setUp(self):
        self.message_handler = MagicMock()
        self.queue = Queue("amqp://localhost", self.message_handler)

    async def test_connect(self, mock_connect):
        await self.queue.connect()

        mock_connect.assert_called_once_with(self.queue.amqp_url)

    async def test_subscribe_without_connect(self, mock_connect):
        with self.assertRaisesMessage(RuntimeError, "Connection not established"):
            await self.queue.subscribe("user_id")

    async def test_subscribe(self, mock_connect):
        await self.queue.connect()

        cancel_subscription = await self.queue.subscribe("user_id")

        # Verify the returned function is callable
        self.assertTrue(callable(cancel_subscription))

        declare_queue = mock_connect.return_value.channel.return_value.declare_queue
        declare_queue.assert_called_once_with(self.queue.QUEUE_PREFIX + "user_id", durable=True)
        declare_queue.return_value.consume.assert_called_once()

    async def test_cancel_subscription(self, mock_connect):
        await self.queue.connect()

        queue = mock_connect.return_value.channel.return_value.declare_queue.return_value
        queue.consume.return_value = "consumer_tag"

        cancel_subscription = await self.queue.subscribe("user_id")

        # Call the cancel function
        await cancel_subscription()

        queue.cancel.assert_called_once_with("consumer_tag")

    async def test_message_processing(self, mock_connect):
        await self.queue.connect()
        await self.queue.subscribe("user_id")

        queue = mock_connect.return_value.channel.return_value.declare_queue.return_value
        callback = queue.consume.call_args[0][0]

        mock_message = MagicMock()
        mock_message.body.decode.return_value = "test_message"

        await callback(mock_message)

        self.message_handler.assert_called_once_with("user_id", "test_message")


@patch("oioioi.notifications.server.server.Queue", autospec=True)
@patch("oioioi.notifications.server.server.Auth", autospec=True)
class ServerTest(TestCase):
    def setUp(self):
        self.port = 8080
        self.amqp_url = "amqp://localhost"
        self.auth_url = "http://example.com"

    def test_initialization(self, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_auth.assert_called_once_with(self.auth_url)
        mock_queue.assert_called_once_with(self.amqp_url, server.handle_rabbit_message)

    @patch("oioioi.notifications.server.server.serve")
    async def test_run(self, mock_serve, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        await server.run()

        mock_auth.return_value.connect.assert_called_once()
        mock_queue.return_value.connect.assert_called_once()
        mock_serve.assert_called_once_with(server.handle_connection, "", self.port)
        mock_serve.return_value.__aenter__.return_value.serve_forever.assert_called_once()

    async def test_register_connection_success(self, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_auth.return_value.authenticate.return_value = "user_id"
        mock_websocket = AsyncMock()

        return_val = await server._register_connection(mock_websocket, "session_id")

        self.assertEqual(return_val, "user_id")
        self.assertIn("user_id", server.users)
        mock_auth.return_value.authenticate.assert_called_once_with("session_id")
        mock_queue.return_value.subscribe.assert_called_once_with("user_id")

    async def test_register_connection_failure(self, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_auth.return_value.authenticate.side_effect = RuntimeError("Authentication failed")
        mock_websocket = AsyncMock()

        return_val = await server._register_connection(mock_websocket, "session_id")

        self.assertEqual(return_val, None)
        self.assertNotIn("user_id", server.users)
        mock_auth.return_value.authenticate.assert_called_once_with("session_id")
        mock_queue.return_value.subscribe.assert_not_called()

    async def test_unregister_connection(self, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        mock_websocket = AsyncMock()
        mock_cancel_subscription = AsyncMock()
        server.users["user_id"] = UserConnection({mock_websocket}, mock_cancel_subscription)

        await server._unregister_connection("user_id", mock_websocket)

        self.assertNotIn("user_id", server.users)
        mock_cancel_subscription.assert_called_once()

    async def test_handle_connection_success(self, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        with patch.object(server, "_register_connection", return_value="user_id"):
            with patch.object(server, "_unregister_connection"):
                mock_websocket = AsyncMock()
                mock_websocket.__aiter__.return_value = [json.dumps({"type": "SOCKET_AUTH", "session_id": "session_id"})]

                await server.handle_connection(mock_websocket)

                mock_websocket.send.assert_called_once_with(json.dumps({"type": "SOCKET_AUTH_RESULT", "status": "OK"}))

    async def test_handle_connection_failure(self, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        with patch.object(server, "_register_connection", return_value=None):
            mock_websocket = AsyncMock()
            mock_websocket.__aiter__.return_value = [json.dumps({"type": "SOCKET_AUTH", "session_id": "session_id"})]

            await server.handle_connection(mock_websocket)

            mock_websocket.send.assert_called_once_with(json.dumps({"type": "SOCKET_AUTH_RESULT", "status": "ERROR"}))

    async def test_handle_connection_multiple_auth(self, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        with patch.object(server, "_register_connection", return_value="user_id") as register_mock:
            with patch.object(server, "_unregister_connection"):
                mock_websocket = AsyncMock()
                auth_message = json.dumps({"type": "SOCKET_AUTH", "session_id": "session_id"})
                mock_websocket.__aiter__.return_value = [auth_message, auth_message]

                await server.handle_connection(mock_websocket)

                # We expect the register_connection to be called only once
                register_mock.assert_called_once_with(mock_websocket, "session_id")

    def test_handle_rabbit_message(self, mock_auth, mock_queue):
        server = Server(self.port, self.amqp_url, self.auth_url)

        cancel_mock = AsyncMock()
        socket_set = set(AsyncMock())
        server.users["user_id"] = UserConnection(socket_set, cancel_mock)

        with patch("oioioi.notifications.server.server.broadcast") as mock_broadcast:
            server.handle_rabbit_message("user_id", "message")
            mock_broadcast.assert_called_once_with(socket_set, "message")
