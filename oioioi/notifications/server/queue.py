import aio_pika
import logging
from typing import Callable, Set, Optional, Dict

class Queue:
    QUEUE_PREFIX = "_notifs_"
    
    def __init__(self, amqp_url: str, on_message: Callable[[str, str], None]):
        self.amqp_url = amqp_url
        self.on_message = on_message
        
        self.logger = logging.getLogger('queue')
        self.connection = None
        self.channel = None

        self.queues: Dict[str, aio_pika.abc.AbstractConsumer] = {}
        
    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(self.amqp_url)
            self.channel = await self.connection.channel()
            self.logger.info("Connected to RabbitMQ")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
    
    async def subscribe(self, username: str):
        # Already subscribed
        if username in self.queues:
            return
            
        try:
            queue_name = self.QUEUE_PREFIX + username
            queue = await self.channel.declare_queue(queue_name)
            
            async def process_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    body = message.body.decode()
                    self.on_message(username, body)
            
            await queue.consume(process_message)

            self.queues[username] = queue
            
            self.logger.info(f"Subscribed to queue for user {username}")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to queue for {username}: {str(e)}")
    
    async def unsubscribe(self, username: str):
        if username in self.queues:
            try:
                await self.queues[username].cancel()
                del self.queues[username]
                self.logger.info(f"Unsubscribed from queue for {username}")
            except Exception as e:
                self.logger.error(f"Error unsubscribing from queue for {username}: {str(e)}")