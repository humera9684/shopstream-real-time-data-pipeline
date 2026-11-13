"""Generate dummy ShopStream data for practicing pipelines (additive; never deletes).

Usage:
    set DATABASE_URL=postgresql://user:pass@localhost:5432/shopstream
    python seed_data.py --users 50 --products 30 --orders 500 --seed 42

Rows created: users, products, orders, order_items, outbox_events (ORDER_CREATED).
Dummy users all share the password "Password123!" (argon2-hashed if argon2 is installed).
"""
import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg
from faker import Faker

CATEGORIES = {
    "Electronics": ["Wireless Earbuds", "Bluetooth Speaker", "Mechanical Keyboard", "USB-C Hub", "Webcam", "Power Bank"],
    "Lifestyle": ["Water Bottle", "Yoga Mat", "Travel Mug", "Tote Bag", "Notebook Set"],
    "Home": ["Scented Candle", "Throw Blanket", "Cutting Board", "Plant Pot", "Wall Clock"],
    "Fashion": ["Denim Jacket", "Wool Scarf", "Leather Wallet", "Sunglasses", "Canvas Cap"],
}
ADJ = ["Classic", "Urban", "Nordic", "Pro", "Eco", "Compact", "Deluxe", "Lite"]
STATUSES = ["placed", "placed", "paid", "shipped", "shipped", "delivered", "delivered", "cancelled"]


def password_hash():
    try:
        from argon2 import PasswordHasher
        return PasswordHasher().hash("Password123!")
    except ImportError:
        return "dummy-hash-not-loginable"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=50)
    ap.add_argument("--products", type=int, default=30)
    ap.add_argument("--orders", type=int, default=500)
    ap.add_argument("--days", type=int, default=90, help="spread order dates over this many days")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()

    rnd = random.Random(a.seed)
    fake = Faker()
    if a.seed is not None:
        Faker.seed(a.seed)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    pw = password_hash()
    run = uuid.uuid4().hex[:6]  # keeps emails unique across repeated runs

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        # users
        users = []
        for i in range(a.users):
            name = fake.name()
            email = f"{name.lower().replace(' ', '.').replace('..', '.')}.{run}{i}@example.com"
            created = now - timedelta(days=rnd.randint(a.days, a.days + 180), minutes=rnd.randint(0, 1440))
            cur.execute("INSERT INTO users (name,email,password_hash,created_at) VALUES (%s,%s,%s,%s) RETURNING id",
                        (name[:120], email[:200], pw, created))
            users.append((cur.fetchone()[0], name, email))

        # products
        for _ in range(a.products):
            cat = rnd.choice(list(CATEGORIES))
            base = rnd.choice(CATEGORIES[cat])
            cur.execute("INSERT INTO products (name,category,description,price,stock,image) VALUES (%s,%s,%s,%s,%s,%s)",
                        (f"{rnd.choice(ADJ)} {base}", cat, fake.sentence(nb_words=8)[:400],
                         Decimal(rnd.randint(5, 300)) + Decimal(rnd.choice(["0.00", "0.50", "0.99"])),
                         rnd.randint(20, 500), base.lower().replace(" ", "-")))
        cur.execute("SELECT id, price FROM products")
        catalog = cur.fetchall()
        all_users = users or [(None, fake.name(), fake.email())]
        if not users:
            cur.execute("SELECT id, name, email FROM users")
            all_users = cur.fetchall() or all_users

        # orders + items + outbox
        for _ in range(a.orders):
            uid, uname, uemail = rnd.choice(all_users)
            created = now - timedelta(seconds=rnd.randint(0, a.days * 86400))
            picks = rnd.sample(catalog, rnd.randint(1, min(5, len(catalog))))
            lines = [(pid, rnd.randint(1, 4), price) for pid, price in picks]
            total = sum((p * q for _, q, p in lines), Decimal("0"))
            cur.execute("INSERT INTO orders (customer_name,customer_email,total,created_at,status,user_id) "
                        "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                        (uname, uemail, total, created, rnd.choice(STATUSES), uid))
            oid = cur.fetchone()[0]
            for pid, q, price in lines:
                cur.execute("INSERT INTO order_items (order_id,product_id,quantity,unit_price) VALUES (%s,%s,%s,%s)",
                            (oid, pid, q, price))
            published = rnd.random() < 0.7
            cur.execute(
                "INSERT INTO outbox_events (event_id,event_type,aggregate_id,payload,status,created_at,published_at) "
                "VALUES (%s,'ORDER_CREATED',%s,%s::jsonb,%s,%s,%s)",
                (str(uuid.uuid4()), oid,
                 json.dumps({"order_id": oid, "event_type": "ORDER_CREATED", "total": str(total),
                             "items": [{"product_id": p, "quantity": q, "unit_price": str(pr)} for p, q, pr in lines]}),
                 "PUBLISHED" if published else "PENDING", created,
                 created + timedelta(seconds=rnd.randint(1, 30)) if published else None))
        conn.commit()
    print(f"Inserted {a.users} users, {a.products} products, {a.orders} orders (+items, +outbox events).")


if __name__ == "__main__":
    main()
