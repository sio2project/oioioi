from typing import Union, Dict, Any, Optional, Callable
from socketify import App, AppOptions, OpCode, CompressOptions, WebSocket
import json
import logging
from auth import Auth
from queue import Queue

class Server:
    def __init__(self):
        self.logger = logging.getLogger('server')
        
        self.app = App()
        self.queue = Queue()
        self.auth = Auth()
        
        # Initialize the socketify app
        app.ws("/*", {
            "message": self.on_ws_message,
            "close": self.on_ws_close,
        })
        
    def on_ws_message(self, ws: WebSocket, msg: str, opcode: OpCode) -> None:
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(msg)
            message_type = data.get("type")
            
            if message_type == "authenticate":    
                session_id = data.get("session_id")
                user_name = self.auth.authenticate(session_id)
                
                if user_name:
                    ws.subscribe(user_name)
                    self.queue.subscribe(user_name)
                    self.logger.info(f"User {user_name} authenticated successfully")
                else:
                    self.logger.info(f"Authentication failed for session {session_id}")
                
                ws.send({status: "OK" if user_name else "ERR_AUTH_FAILED"})
                
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            
    def on_ws_close(self, ws: WebSocket, code: int, msg: Union[bytes, str]) -> None:
        """Handle WebSocket connection closure."""
        try:
            # We can retrieve the user name for this WebSockets by checking the topics this WebSocket is subscribed to.
            user_name = ws.get_topics()[0]
            
            if user_name:
                ws.unsubscribe(user_name)
                
                # If there are no more active connections for this user, unsubscribe from the RabbitMQ queue
                if self.app.num_subscribers(user_name) == 0:
                    self.queue.unsubscribe(user_name)
                    
        except Exception as e:
            self.logger.error(f"Error during connection close: {str(e)}")
        
    def on_rabbit_message(self, user_name: str, msg: str) -> None:
        """Handle messages from RabbitMQ."""
        try:
            self.logger.debug(f"Publishing message to {user_name}: {msg}")
            self.app.publish(user_name, msg)
        except Exception as e:
            self.logger.error(f"Error publishing message: {str(e)}")
    
    async def run(self) -> None:
        """Start the notification server."""
        try:
            # Connect to RabbitMQ
            await self.queue.connect()
            
            # Start the server
            self.logger.info(f"Starting notification server on port {port}")
            self.app.listen(7887)
            self.app.run()
            
        except Exception as e:
            self.logger.error(f"Error running server: {str(e)}")
            raise