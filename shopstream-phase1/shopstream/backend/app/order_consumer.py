
import json
import logging
import os

from confluent_kafka import Consumer, KafkaException
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True
)

consumer = Consumer({
    "bootstrap.servers": os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"
    ),
    "group.id": os.getenv(
    "KAFKA_CONSUMER_GROUP",
    "shopstream-order-consumers"
    ),
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False
})

consumer.subscribe(["orders.created"])


def process_order(event):
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO processed_order_events (
                    event_id, order_id, event_type
                )
                VALUES (
                    :event_id, :order_id, :event_type
                )
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id
            """),
            {
                "event_id": event["event_id"],
                "order_id": str(event["order_id"]),
                "event_type": event["event_type"]
            }
        ).scalar_one_or_none()

        if result is None:
            logger.info(
                "Duplicate event skipped: %s",
                event["event_id"]
            )
            return

        logger.info(
            "Processing order %s, total $%s",
            event["order_id"],
            event["total"]
        )

        # Future database processing goes here,
        # inside the same transaction.


def main():
    logger.info("Kafka consumer started")

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue

            if msg.error():
                raise KafkaException(msg.error())

            try:
                event = json.loads(
                    msg.value().decode("utf-8")
                )

                process_order(event)

                # Commit Kafka offset after database success
                consumer.commit(
                    message=msg,
                    asynchronous=False
                )

            except Exception:
                logger.exception(
                    "Failed to process Kafka message"
                )
                # Do not skip failed events
                raise

    finally:
        consumer.close()


if __name__ == "__main__":
    main()
