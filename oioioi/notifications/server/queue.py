import aio_pika
import logging
from typing import Callable, Dict, Tuple, Optional


class Queue:
    QUEUE_PREFIX = "_notifs_"
    
    def __init__(self, amqp_url: str, on_message: Callable[[str, str], None]):
        self.amqp_url = amqp_url
        self.on_message = on_message
        
        self.logger = logging.getLogger('oioioi')
        self.connection: Optional[aio_pika.abc.AbstractConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None

        self.queues: Dict[str, Tuple[aio_pika.abc.AbstractQueue, str]] = {}
        
    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        self.logger.info("Connected to RabbitMQ")
    
    async def subscribe(self, user_id: str):
        if self.connection is None or self.channel is None:
            raise RuntimeError("Connection not established. Call connect() first.")

        if user_id in self.queues:
            self.logger.debug(f"Already subscribed to queue for user {user_id}")
            return
            
        queue_name = self.QUEUE_PREFIX + user_id
        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        async def process_message(message: aio_pika.abc.AbstractIncomingMessage):
            async with message.process():
                body = message.body.decode()
                self.on_message(user_id, body)
        
        consumer_tag = await queue.consume(process_message)

        self.queues[user_id] = (queue, consumer_tag)
        
        self.logger.debug(f"Subscribed to queue for user {user_id}")
    
    async def unsubscribe(self, user_id: str) -> None:
        if self.connection is None or self.channel is None:
            raise RuntimeError("Connection not established. Call connect() first.")
            
        if user_id in self.queues:
            queue, consumer_tag = self.queues[user_id]
            await queue.cancel(consumer_tag)
            del self.queues[user_id]

            self.logger.debug(f"Unsubscribed from queue for {user_id}")