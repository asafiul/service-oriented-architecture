from aiokafka import AIOKafkaProducer
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class KafkaProducerClient:
    def __init__(self):
        self.producer = None
        self.bootstrap_servers = settings.kafka_bootstrap_servers
    
    async def start(self):
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await self.producer.start()
            logger.info(f"Kafka producer started: {self.bootstrap_servers}")
        except Exception as e:
            logger.warning(f"Failed to start Kafka producer: {e}. Running without Kafka.")
            self.producer = None
    
    async def stop(self):
        if self.producer:
            await self.producer.stop()
    
    async def send_event(self, topic: str, event: dict):
        if not self.producer:
            logger.warning(f"Kafka producer not available. Event not sent: {topic}")
            return
        
        try:
            await self.producer.send_and_wait(topic, event)
            logger.info(f"Event sent to Kafka topic '{topic}': {event}")
        except Exception as e:
            logger.error(f"Failed to send event to Kafka: {e}")

kafka_producer = KafkaProducerClient()
