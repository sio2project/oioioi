import aio_pika
import logging
from typing import Callable, Set, Optional, Dict, Tuple

class Queue:
    QUEUE_PREFIX = "_notifs_"
    
    def __init__(self, amqp_url: str, on_message: Callable[[str, str], None]):
        self.amqp_url = amqp_url
        self.on_message = on_message
        
        self.logger = logging.getLogger('queue')
        self.connection = None
        self.channel = None

        self.queues: Dict[str, Dict[str, Tuple[aio_pika.Queue, str]]] = {}
        
    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        self.logger.info("Connected to RabbitMQ")
    
    async def subscribe(self, user_id: str):
        # Already subscribed
        if user_id in self.queues:
            return
            
        try:
            queue_name = self.QUEUE_PREFIX + user_id
            queue = await self.channel.declare_queue(queue_name, durable=True)
            
            async def process_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    body = message.body.decode()
                    self.on_message(user_id, body)
            
            consumer_tag = await queue.consume(process_message)

            self.queues[user_id] = (queue, consumer_tag)
            
            self.logger.info(f"Subscribed to queue for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to queue for {user_id}: {str(e)}")
    
    async def unsubscribe(self, user_id: str):
        if user_id in self.queues:
            try:
                queue, consumer_tag = self.queues[user_id]
                await queue.cancel(consumer_tag)
                del self.queues[user_id]

                self.logger.info(f"Unsubscribed from queue for {user_id}")
            except Exception as e:
                self.logger.error(f"Error unsubscribing from queue for {user_id}: {str(e)}")