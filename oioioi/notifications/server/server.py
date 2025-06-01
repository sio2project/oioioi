from typing import Union
from socketify import App, OpCode, WebSocket
import json
import logging
from .auth import Auth
from .queue import Queue


class Server:
    def __init__(self, port: int, amqp_url: str, auth_url: str) -> None:
        self.port = port

        self.app = App()
        self.auth = Auth(auth_url)
        self.queue = Queue(amqp_url, self.on_rabbit_message)
        self.logger = logging.getLogger('oioioi')

        self.app.on_start(self.on_start)
        self.app.ws("/", {
            "upgrade": self.on_ws_upgrade,
            "message": self.on_ws_message,
            "close": self.on_ws_close,
        })

    def run(self) -> None:
        """Start the notification server."""
        self.logger.info(f"Starting notification server on port {self.port}")
        self.app.listen(self.port)
        self.app.run()

    async def on_start(self) -> None:
        await self.auth.connect()
        await self.queue.connect()

    def on_ws_upgrade(self, res, req, socket_context):
        """ 
        Taken from socketify's documentation.
        This method allows for storing extra data inside the websocket object. 
        """

        key = req.get_header("sec-websocket-key")
        protocol = req.get_header("sec-websocket-protocol")
        extensions = req.get_header("sec-websocket-extensions")

        user_data = {"user_id": None}

        res.upgrade(key, protocol, extensions, socket_context, user_data)

    async def on_ws_message(self, ws: WebSocket, msg: Union[bytes, str], opcode: OpCode) -> None:
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(msg)
            message_type = data.get("type")

            if message_type == "SOCKET_AUTH":
                await self.on_ws_auth_message(ws, data.get("session_id"))
            else:
                self.logger.warning(f"Unknown message type: {message_type}")

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")

    async def on_ws_close(self, ws: WebSocket, code: int, msg: Union[bytes, str]) -> None:
        """Handle WebSocket connection closure."""
        try:
            user_id = ws.get_user_data().get("user_id")

            # If there are no more active connections for this user, unsubscribe from the RabbitMQ queue
            if user_id and self.app.num_subscribers(user_id) == 0:
                await self.queue.unsubscribe(user_id)
                
            self.logger.debug(f"WebSocket closed for user {user_id}")

        except Exception as e:
            self.logger.error(f"Error during connection close: {str(e)}")

    def on_rabbit_message(self, user_name: str, msg: str) -> None:
        """Handle messages from RabbitMQ."""
        try:
            self.logger.debug(f"Publishing message to {user_name}: {msg}")
            self.app.publish(user_name, msg, OpCode.TEXT)
        except Exception as e:
            self.logger.error(f"Error publishing message: {str(e)}")

    async def on_ws_auth_message(self, ws: WebSocket, session_id: str) -> None:
        try:
            user_id = await self.auth.authenticate(session_id)

            ws.subscribe(user_id)
            ws.get_user_data()["user_id"] = user_id
            await self.queue.subscribe(user_id)

            self.logger.debug(f"User {user_id} authenticated successfully")
            ws.send({"type": "SOCKET_AUTH_RESULT", "status": "OK"}, OpCode.TEXT)

        except Exception as e:
            self.logger.error(
                f"Authentication error for session {session_id}: {str(e)}")
            ws.send({"type": "SOCKET_AUTH_RESULT",
                    "status": "ERR_AUTH_FAILED"}, OpCode.TEXT)
