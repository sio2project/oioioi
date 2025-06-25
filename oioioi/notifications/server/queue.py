import aio_pika
import logging
from typing import Callable, Optional, Awaitable


class Queue:
    QUEUE_PREFIX = "_notifs_"
    
    def __init__(self, amqp_url: str, on_message: Callable[[str, str], None]):
        """
        Args:
            amqp_url: Connection URL for RabbitMQ
            on_message: Callback function that receives (user_id, message)
        """
        self.amqp_url = amqp_url
        self.on_message = on_message
        
        self.logger = logging.getLogger(__name__)
        self.connection: Optional[aio_pika.abc.AbstractConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        
    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        self.logger.info("Connected to RabbitMQ")
    
    async def close(self):
        if self.connection:
            await self.connection.close()
            self.connection = self.channel = None
            self.logger.info("RabbitMQ connection closed")
    
    async def subscribe(self, user_id: str) -> Callable[[], Awaitable[None]]:
        """
        Subscribe to a user's queue.
        The on_message callback will be called with (user_id, message) for each message received.
        
        Returns:
            A function that, when called, will cancel the subscription.
        """
        if self.connection is None or self.channel is None:
            raise RuntimeError("Connection not established. Call connect() first.")
            
        queue_name = self.QUEUE_PREFIX + user_id
        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        async def process_message(message: aio_pika.abc.AbstractIncomingMessage):
            async with message.process():
                body = message.body.decode()
                self.on_message(user_id, body)
        
        consumer_tag = await queue.consume(process_message)
        
        self.logger.debug(f"Subscribed to queue for user {user_id}")
        
        async def cancel_subscription():
            try:
                await self.channel.ready() # type: ignore
                await queue.cancel(consumer_tag)
                self.logger.debug(f"Unsubscribed from queue for {user_id}")
            except Exception as e:
                self.logger.error(f"Error unsubscribing from queue for {user_id}: {e}")
                
        return cancel_subscription