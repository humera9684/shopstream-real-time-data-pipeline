
import os
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import create_engine, text

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    StructType, StructField, StringType,
    IntegerType, ArrayType
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopstream-analytics")

# PostgreSQL connection
engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True
)

# Spark session
spark = (
    SparkSession.builder
    .appName("ShopStreamSalesAnalytics")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

# Kafka event schema
item_schema = StructType([
    StructField("product_id", IntegerType()),
    StructField("quantity", IntegerType()),
    StructField("unit_price", StringType())
])

order_schema = StructType([
    StructField("event_id", StringType()),
    StructField("order_id", StringType()),
    StructField("event_type", StringType()),
    StructField("total", StringType()),
    StructField("items", ArrayType(item_schema))
])

# Read Kafka events
kafka_df = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:29092")
    .option("subscribe", "orders.created")
    .option("startingOffsets", "earliest")
    .load()
)

# Parse JSON into columns
orders_df = (
    kafka_df
    .select(
        from_json(
            col("value").cast("string"),
            order_schema
        ).alias("data")
    )
    .select("data.*")
)


def save_order_event(event):
    # Validate before writing
    event_id = str(UUID(event["event_id"]))
    order_id = str(event["order_id"])

    if event["event_type"] != "ORDER_CREATED":
        raise ValueError("Unexpected event type")

    items = event["items"]
    if not items:
        raise ValueError("Order has no items")

    # All updates for one event are atomic
    with engine.begin() as conn:

        result = conn.execute(
            text("""
                INSERT INTO analytics_processed_events
                    (event_id, order_id)
                VALUES (:event_id, :order_id)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id
            """),
            {
                "event_id": event_id,
                "order_id": order_id
            }
        ).scalar_one_or_none()

        if result is None:
            logger.info(
                "Duplicate event skipped: %s",
                event_id
            )
            return

        # Update product-level running totals
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            unit_price = Decimal(item["unit_price"])

            if product_id is None or quantity is None:
                raise ValueError("Invalid order item")

            if quantity <= 0 or unit_price < 0:
                raise ValueError("Invalid quantity or price")

            revenue = quantity * unit_price

            conn.execute(
                text("""
                    INSERT INTO product_sales (
                        product_id,
                        units_sold,
                        total_revenue,
                        order_lines
                    )
                    VALUES (
                        :product_id,
                        :quantity,
                        :revenue,
                        1
                    )
                    ON CONFLICT (product_id)
                    DO UPDATE SET
                        units_sold =
                            product_sales.units_sold
                            + EXCLUDED.units_sold,
                        total_revenue =
                            product_sales.total_revenue
                            + EXCLUDED.total_revenue,
                        order_lines =
                            product_sales.order_lines
                            + EXCLUDED.order_lines,
                        updated_at = NOW()
                """),
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "revenue": revenue
                }
            )

    logger.info("Processed order %s", order_id)


def write_to_postgres(batch_df, batch_id):
    logger.info("Processing Spark batch %s", batch_id)

    # Iterate through the records without collecting
    # the entire batch into one Python list.
    for row in batch_df.toLocalIterator():
        event = row.asDict(recursive=True)
        save_order_event(event)

    logger.info("Batch %s completed", batch_id)


query = (
    orders_df.writeStream
    .foreachBatch(write_to_postgres)
    .option(
        "checkpointLocation",
        "/opt/spark/checkpoints/postgres_sales_v1"
    )
    .trigger(processingTime="10 seconds")
    .start()
)

logger.info("ShopStream analytics streaming started")

try:
    query.awaitTermination()
finally:
    engine.dispose()
    spark.stop()
