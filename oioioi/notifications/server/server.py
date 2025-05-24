import asyncio
from typing import Union, Dict, Any, Optional, Callable
from socketify import App, AppOptions, OpCode, CompressOptions, WebSocket
import json
import logging
from . auth import Auth
from . queue import Queue

class Server:
    def __init__(self, port: int, amqp_url: str, auth_url: str) -> None:
        self.port = port
        
        self.app = App()
        self.auth = Auth(auth_url)
        self.queue = Queue(amqp_url, self.on_rabbit_message)
        self.logger = logging.getLogger('server')
        
        self.app.on_start(self.on_start)
        self.app.ws("/", {
            "message": self.on_ws_message,
            "close": self.on_ws_close,
        })
        
        
    def run(self) -> None:
        """Start the notification server."""
        logging.basicConfig(level=logging.INFO)

        self.logger.info(f"Starting notification server on port {self.port}")

        self.app.listen(self.port)
        self.app.run()
        
    async def on_start(self) -> None:
        await self.auth.connect()
        await self.queue.connect()
        
    async def on_ws_message(self, ws: WebSocket, msg: str, opcode: OpCode) -> None:
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(msg)
            message_type = data.get("type")
            
            if message_type == "SOCKET_AUTH":    
                session_id = data.get("session_id")
                user_name = await self.auth.authenticate(session_id)
                
                if user_name:
                    ws.subscribe(user_name)
                    await self.queue.subscribe(user_name)
                    self.logger.info(f"User {user_name} authenticated successfully")
                else:
                    self.logger.info(f"Authentication failed for session {session_id}")
                
                ws.send({"type": "SOCKET_AUTH_RESULT", "status": "OK" if user_name else "ERR_AUTH_FAILED"}, OpCode.TEXT)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            
    async def on_ws_close(self, ws: WebSocket, code: int, msg: Union[bytes, str]) -> None:
        """Handle WebSocket connection closure."""
        try:
            # We can retrieve the user name for this WebSockets by checking the topics this WebSocket is subscribed to.
            user_name = ws.get_topics()[0]
            
            if user_name:
                ws.unsubscribe(user_name)
                
                # If there are no more active connections for this user, unsubscribe from the RabbitMQ queue
                if self.app.num_subscribers(user_name) == 0:
                    await self.queue.unsubscribe(user_name)
                    
        except Exception as e:
            self.logger.error(f"Error during connection close: {str(e)}")
        
    def on_rabbit_message(self, user_name: str, msg: str) -> None:
        """Handle messages from RabbitMQ."""
        try:
            self.logger.debug(f"Publishing message to {user_name}: {msg}")
            self.app.publish(user_name, msg, OpCode.TEXT)
        except Exception as e:
            self.logger.error(f"Error publishing message: {str(e)}")