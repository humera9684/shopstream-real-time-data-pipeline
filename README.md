# ShopStream

A learning project that builds an end-to-end, event-driven data pipeline on top of a small storefront.

Customers place orders in a React storefront. A FastAPI backend saves them to PostgreSQL, publishes an `ORDER_CREATED` event to Kafka using the transactional outbox pattern, and Spark Structured Streaming turns those events into per-product sales totals.

> Payments are **simulated**. Do not enter real payment information.

## Architecture

```
React (web) ──▶ FastAPI (api) ──▶ PostgreSQL
                                   │  orders, order_items, outbox_events
                                   ▼
                          outbox-publisher
                                   │  reads PENDING events, sends to Kafka,
                                   ▼  marks them PUBLISHED after Kafka confirms
                           Kafka topic: orders.created
                              │                 │
                              ▼                 ▼
                       order-consumer        Spark (analytics profile)
                       de-duplicates and     product totals: units sold,
                       records each event    revenue, order lines
```

| Service | What it does |
|---|---|
| `web` | React + Vite storefront (http://localhost:5173) |
| `api` | FastAPI backend with auth, products and orders (http://localhost:8000, docs at `/docs`) |
| `kafka` | Single-node Kafka in KRaft mode |
| `outbox-publisher` | Moves outbox rows from Postgres to Kafka, with idempotent producer settings and `acks=all` |
| `order-consumer` | Reads `orders.created`, skips duplicate `event_id`s, commits offsets only after the database write succeeds |
| `spark` | Streaming job (`backend/spark/jobs/order_stream.py`) that aggregates sales by product. Runs only with the `analytics` profile |

### Why an outbox?

When an order is saved, the API writes an event row to `outbox_events` **in the same transaction**. An order therefore can't exist without its event, and the reverse. The publisher delivers the event to Kafka afterwards.

## Prerequisites

- Docker Desktop
- A PostgreSQL database reachable from the containers. The compose file expects it on your host machine, via `host.docker.internal`.

## Configuration

Create a `.env` file next to `docker-compose.yml`. **Do not commit it.**

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@host.docker.internal:5432/shopstream
JWT_SECRET=change-me-to-a-long-random-string
```

Optional: `COOKIE_SECURE=true` when serving over HTTPS.

## Run

From the `shopstream` folder:

```powershell
docker compose up --build -d
```

Create the Kafka topic once (auto-creation is disabled):

```powershell
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --create --topic orders.created --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
```

Then open:

- Storefront: http://localhost:5173
- API docs: http://localhost:8000/docs

On first start the API creates the `users`, `refresh_tokens`, `products`, `orders` and `order_items` tables and seeds the product catalog. Products missing from the seed list are added on later starts.

### Database tables created outside the app

`outbox_events` and `processed_order_events` are used by the API, publisher and consumer, but **no SQL in this repo creates them**. They need to exist before orders can be published. Adding a `schema.sql` for them is a good next step.

### Run the Spark job

```powershell
docker compose --profile analytics up spark
```

The first run downloads the Kafka connector with Ivy, which can take a minute or two. Results print to the console every 10 seconds as a running scoreboard.

## Try it

1. Create an account in the storefront and add products to the bag.
2. Click **Place test order**.
3. Watch the event flow:
   ```powershell
   docker compose logs -f outbox-publisher order-consumer
   ```
4. With the Spark job running, see the product totals update in its console output.

To see the topic's partitions: `docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --describe --topic orders.created --bootstrap-server localhost:9092`

## Generate sample data

`seed_data.py` adds users, products, orders, order items and outbox events. It only adds rows and never deletes.

```powershell
$env:DATABASE_URL = "postgresql://USER:PASSWORD@localhost:5432/shopstream"
python seed_data.py --users 50 --products 30 --orders 500 --seed 42
```

It needs `psycopg` and `faker`. Seeded users all share the password `Password123!`.

## API overview

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/products` | Product catalog |
| POST | `/auth/register`, `/auth/login` | Return a 15-minute access token; set an httpOnly refresh cookie |
| POST | `/auth/refresh` | Rotates the refresh token (7-day lifetime) |
| POST | `/auth/logout` | Revokes the refresh token |
| POST | `/orders` | Requires auth. Checks stock, writes the order, items, stock change and outbox event in one transaction |
| GET | `/orders` | The signed-in user's orders |

## Useful commands

```powershell
docker compose logs -f api          # API logs
docker compose restart api          # pick up backend changes if needed
docker compose down                 # stop; keeps Kafka and Postgres data
```

Avoid `docker compose down -v` unless you want to erase Kafka's data and the Spark checkpoints.

## Project layout

```
backend/app/            FastAPI app, outbox publisher, order consumer
backend/spark/jobs/     Spark Structured Streaming job
frontend/               React + Vite storefront
seed_data.py            Sample data generator
docker-compose.yml      All services
```

## Known gaps and next steps


- Add a `schema.sql` for the outbox and processed-events tables.
- Add tests for the order transaction and the Spark aggregation.
- Events created by `seed_data.py` don't include `event_id` inside the JSON payload, which the consumer and Spark expect.
