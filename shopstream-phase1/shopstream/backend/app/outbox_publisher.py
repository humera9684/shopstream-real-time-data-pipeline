
import json
import logging
import os
import time

from confluent_kafka import Producer
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
KAFKA_SERVER = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"
)

TOPIC = "orders.created"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

producer = Producer({
    "bootstrap.servers": KAFKA_SERVER,
    "enable.idempotence": True,
    "acks": "all"
})


def publish_one_event():
    # Lock one pending event to prevent
    # other publishers from selecting it.
    with engine.begin() as conn:
        event = conn.execute(
            text("""
                SELECT id, aggregate_id, payload
                FROM outbox_events
                WHERE status = 'PENDING'
                ORDER BY created_at, id
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)
        ).mappings().first()

        if not event:
            return False

        event_id = str(event["id"])
        order_id = str(event["aggregate_id"])
        payload = json.dumps(event["payload"])

        logger.info("Publishing event %s", event_id)

        delivery_error = []

        def delivery_callback(err, msg):
            if err is not None:
                delivery_error.append(str(err))

        producer.produce(
            topic=TOPIC,
            key=order_id,
            value=payload.encode("utf-8"),
            on_delivery=delivery_callback
        )

        remaining = producer.flush(timeout=15)

        if remaining > 0 or delivery_error:
            raise RuntimeError(
                f"Kafka delivery not confirmed: "
                f"{delivery_error or 'timeout'}"
            )

        conn.execute(
            text("""
                UPDATE outbox_events
                SET status = 'PUBLISHED',
                    published_at = NOW()
                WHERE id = :event_id
            """),
            {"event_id": event_id}
        )

        logger.info(
            "Event %s acknowledged by Kafka",
            event_id
        )
        return True


def main():
    logger.info("Outbox publisher started")

    while True:
        try:
            published = publish_one_event()

            if not published:
                time.sleep(2)

        except KeyboardInterrupt:
            break

        except Exception:
            logger.exception("Publisher error")
            time.sleep(5)


if __name__ == "__main__":
    main()
