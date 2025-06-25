import asyncio
import json
import logging
from typing import Dict, NamedTuple, Set, Callable, Awaitable, Optional
from weakref import WeakValueDictionary

from websockets.asyncio.server import serve, ServerConnection, broadcast
from websockets.exceptions import ConnectionClosed

from oioioi.notifications.server.auth import Auth
from oioioi.notifications.server.queue import Queue


class UserConnection(NamedTuple):
    sockets: Set[ServerConnection]
    queue_cancel: Callable[[], Awaitable[None]]

class Server:
    def __init__(self, port: int, amqp_url: str, auth_url: str) -> None:
        self.port = port
        self.auth = Auth(auth_url)
        self.queue = Queue(amqp_url, self.handle_rabbit_message)
        self.logger = logging.getLogger('oioioi')
        
        self.users: Dict[str, UserConnection] = {}
        # Per-user locks to prevent race conditions when registering connections
        self.user_locks = WeakValueDictionary[str, asyncio.Lock]()

    async def run(self) -> None:
        self.logger.info(f"Starting notification server on port {self.port}")
        
        try:
            await self.auth.connect()
            await self.queue.connect()                
            
            async with serve(self.handle_connection, "", self.port) as server:
                self.logger.info("Notification server started successfully")
                await server.serve_forever()
            
        finally:
            await self.auth.close()
            await self.queue.close()
            
            self.logger.info("Notification server stopped")

    async def handle_connection(self, websocket: ServerConnection) -> None:
        user_id = None
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data["type"]

                    if message_type == "SOCKET_AUTH":
                        if user_id is not None:
                            raise RuntimeError("Socket is already authenticated.")
                        
                        user_id = await self._register_connection(websocket, data["session_id"])
                        
                        await websocket.send(json.dumps({
                            "type": "SOCKET_AUTH_RESULT", 
                            "status": "OK" if user_id else "ERROR"
                        }))
                    else:
                        raise RuntimeError("Unknown message type.")
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {type(e).__name__}, {e}")
        
        except ConnectionClosed:
            # Ignore connection close to avoid logging them as errors
            pass
        
        finally:
            await self._unregister_connection(user_id, websocket)
                
    def handle_rabbit_message(self, user_id: str, msg: str) -> None:
        if user_id not in self.users:
            self.logger.warning(f"Received message for unregistered user {user_id}")
            return
        
        broadcast(self.users[user_id].sockets, msg)
        self.logger.debug(f"Published message to {user_id}: {msg}")
        
    async def _register_connection(self, websocket: ServerConnection, session_id: str) -> Optional[str]:
        try:
            user_id = await self.auth.authenticate(session_id)
            
            # Create or get the lock for the user
            lock = self.user_locks.setdefault(user_id, asyncio.Lock())
                
            # Acquire the lock to ensure that we only subscribe to the queue once per user
            async with lock:
                if user_id not in self.users:
                    # User is not registered, try subscribing to its queue
                    queue_cancel = await self.queue.subscribe(user_id)
                    self.users[user_id] = UserConnection(set(), queue_cancel)
                
                self.users[user_id].sockets.add(websocket)

            self.logger.debug(f"User {user_id} authenticated successfully")
            return user_id

        except Exception as e:
            self.logger.error(f"Authentication error for session {session_id}: {type(e).__name__}, {e}")
            return None
    
    async def _unregister_connection(self, user_id: Optional[str], websocket: ServerConnection) -> None:
        if user_id is None:
            self.logger.debug("WebSocket closed for unregistered user.")
            return
        
        self.users[user_id].sockets.remove(websocket)
        
        if not self.users[user_id].sockets:
            # Cleanup if there are no more sockets for this user
            queue_cancel = self.users[user_id].queue_cancel

            del self.users[user_id]
            
            await queue_cancel()
                
        self.logger.debug(f"WebSocket closed for user {user_id}")