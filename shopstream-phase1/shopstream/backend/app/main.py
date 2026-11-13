from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import os
import secrets
from typing import Annotated
import uuid
from sqlalchemy import text
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import ForeignKey, Numeric, String, create_engine, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from app.analytics_router import router as analytics_router

import json

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
SessionLocal = sessionmaker(engine)

SECRET = os.environ["JWT_SECRET"]
ACCESS_MINUTES = 15
REFRESH_DAYS = 7
REFRESH_COOKIE = "refresh_token"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]
    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(400))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(default=0)
    image: Mapped[str] = mapped_column(String(300))


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_email: Mapped[str] = mapped_column(String(200))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    status: Mapped[str] = mapped_column(String(30), default="placed")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped[Order] = relationship(back_populates="items")


SEED = [
    ("Studio Headphones", "Electronics", "Rich sound, all-day comfort.", "129.00", 45, "headphones"),
    ("Everyday Backpack", "Lifestyle", "Room for your commute and weekend plans.", "68.00", 70, "backpack"),
    ("Ceramic Coffee Set", "Home", "A slow morning essential.", "42.00", 35, "coffee"),
    ("Smart Desk Lamp", "Electronics", "Adjustable warm and cool lighting.", "89.00", 28, "lamp"),
    ("Running Sneakers", "Fashion", "Lightweight style for everyday movement.", "110.00", 60, "shoes"),
    ("Minimalist Watch", "Fashion", "A timeless everyday accessory.", "155.00", 22, "watch"),
    ("Instant Film Camera", "Electronics", "Snap it, shake it, keep the memory.", "99.00", 30, "camera"),
    ("Velvet Sofa", "Home", "Deep green comfort for any living room.", "749.00", 8, "sofa"),
    ("Latte Cup Duo", "Home", "Two double-walled cups for café mornings.", "26.00", 80, "latte"),
    ("Classic Sunglasses", "Fashion", "Timeless frames with UV protection.", "79.00", 55, "sunglasses"),
    ("Leather Handbag", "Fashion", "Structured, roomy and ready for any occasion.", "185.00", 18, "handbag"),
    ("Yoga Mat", "Sports", "Non-slip grip for flows and floor work.", "35.00", 90, "yoga"),
    ("Dumbbell Set", "Sports", "Pair of adjustable weights for home workouts.", "64.00", 40, "dumbbells"),
    ("Barbell Training Set", "Sports", "Olympic bar with plates for serious lifting.", "219.00", 12, "barbell"),
    ("Hydrating Face Cream", "Beauty", "Lightweight daily moisture for all skin types.", "28.00", 100, "cream"),
    ("Makeup Brush Set", "Beauty", "Soft, dense brushes for a flawless finish.", "39.00", 65, "makeup"),
    ("Startup Book Bundle", "Books", "A stack of essential reads for founders.", "58.00", 25, "books"),
    ("Poetry Collection", "Books", "Short, honest verses for slow evenings.", "14.00", 75, "poetry"),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        existing = set(db.scalars(select(Product.name)))
        for name, category, description, price, stock, image in SEED:
            if name not in existing:
                db.add(Product(name=name, category=category, description=description,
                               price=Decimal(price), stock=stock, image=image))
    yield


app = FastAPI(title="ShopStream API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True,
                   allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(analytics_router)

def session():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(session)]
hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def make_token(user: User):
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_MINUTES)
    return jwt.encode({"sub": str(user.id), "exp": exp}, SECRET, algorithm="HS256")


def user_json(u: User):
    return {"id": u.id, "name": u.name, "email": u.email}


def hash_token(raw: str):
    return hashlib.sha256(raw.encode()).hexdigest()


def start_session(db: Session, user: User, response: Response):
    """Issue a new refresh token (httpOnly cookie) and a short-lived access token."""
    raw = secrets.token_urlsafe(48)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(raw),
                        expires_at=utcnow() + timedelta(days=REFRESH_DAYS)))
    db.commit()
    response.set_cookie(REFRESH_COOKIE, raw, max_age=REFRESH_DAYS * 86400, httponly=True,
                        samesite="lax", secure=COOKIE_SECURE, path="/auth")
    return {"token": make_token(user), "user": user_json(user)}


def current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        uid = int(jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, "Unknown user")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


class LineInput(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=50)


class RegisterInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class OrderInput(BaseModel):
    items: list[LineInput] = Field(min_length=1)


def product_json(p: Product):
    return {"id": p.id, "name": p.name, "category": p.category,
            "description": p.description, "price": str(p.price),
            "stock": p.stock, "image": p.image}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", status_code=201)
def register(p: RegisterInput, response: Response, db: DB):
    email = p.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(name=p.name.strip(), email=email, password_hash=hasher.hash(p.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return start_session(db, user, response)


@app.post("/auth/login")
def login(p: LoginInput, response: Response, db: DB):
    user = db.scalar(select(User).where(User.email == p.email.lower()))
    try:
        if not user:
            raise VerifyMismatchError
        hasher.verify(user.password_hash, p.password)
    except VerifyMismatchError:
        raise HTTPException(401, "Incorrect email or password")
    return start_session(db, user, response)


@app.post("/auth/refresh")
def refresh(response: Response, db: DB,
            refresh_token: Annotated[str | None, Cookie()] = None):
    if not refresh_token:
        raise HTTPException(401, "No refresh token")
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
    if not row:
        raise HTTPException(401, "Invalid refresh token")
    if row.revoked:
        # A rotated token was used again: assume theft and end every session for this user.
        db.execute(update(RefreshToken).where(RefreshToken.user_id == row.user_id).values(revoked=True))
        db.commit()
        raise HTTPException(401, "Refresh token reuse detected")
    if row.expires_at < utcnow():
        raise HTTPException(401, "Refresh token expired")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(401, "Unknown user")
    row.revoked = True  # rotation: each refresh token works once
    db.flush()
    return start_session(db, user, response)


@app.post("/auth/logout")
def logout(response: Response, db: DB,
           refresh_token: Annotated[str | None, Cookie()] = None):
    if refresh_token:
        row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
        if row:
            row.revoked = True
            db.commit()
    response.delete_cookie(REFRESH_COOKIE, path="/auth")
    return {"ok": True}


@app.get("/products")
def products(db: DB):
    return [product_json(p) for p in db.scalars(select(Product).order_by(Product.id))]


@app.post("/orders", status_code=201)

def create_order(payload: OrderInput, db: DB, user: CurrentUser):
    customer_name = user.name
    customer_email = user.email
    user_id = user.id

    quantities = {}

    for line in payload.items:
        quantities[line.product_id] = (
            quantities.get(line.product_id, 0) + line.quantity
        )

    if not quantities:
        raise HTTPException(400, "Order must contain items")

    if any(qty <= 0 for qty in quantities.values()):
        raise HTTPException(400, "Quantity must be positive")

    try:
        # Lock products to prevent overselling
        products = db.scalars(
            select(Product)
            .where(Product.id.in_(quantities))
            .order_by(Product.id)
            .with_for_update()
        ).all()

        found = {p.id: p for p in products}

        # Validate products and stock
        for product_id, quantity in quantities.items():
            product = found.get(product_id)

            if not product:
                raise HTTPException(
                    404,
                    f"Product {product_id} not found"
                )

            if product.stock < quantity:
                raise HTTPException(
                    409,
                    f"Not enough stock for {product.name}"
                )

        # Calculate total
        total = sum(
            (
                found[pid].price * qty
                for pid, qty in quantities.items()
            ),
            Decimal("0")
        )

        # Create order
        order = Order(
            customer_name=customer_name,
            customer_email=customer_email,
            total=total,
            user_id=user_id
        )

        db.add(order)
        db.flush()  # Generates order.id

        # Create order items and update inventory
        items_payload = []

        for pid, qty in quantities.items():
            product = found[pid]
            product.stock -= qty

            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=pid,
                    quantity=qty,
                    unit_price=product.price
                )
            )

            items_payload.append({
                "product_id": pid,
                "quantity": qty,
                "unit_price": str(product.price)
            })
        event_id = str(uuid.uuid4())
        event_payload = {
            "event_id": event_id,
            "order_id": str(order.id),
            "event_type": "ORDER_CREATED",
            "total": str(total),
            "items": items_payload
        }
        # Insert outbox event into SAME transaction
        db.execute(
            text("""
                INSERT INTO outbox_events (
                    id,
                    aggregate_type,
                    aggregate_id,
                    event_type,
                    payload
                )
                VALUES (
                    :event_id,
                    :aggregate_type,
                    :aggregate_id,
                    :event_type,
                    CAST(:payload AS jsonb)
                )
            """),
            {
                "event_id": event_id,
                "aggregate_type": "ORDER",
                "aggregate_id": str(order.id),
                "event_type": "ORDER_CREATED",
                "payload": json.dumps(event_payload)
            }
        )
        order_id = order.id

        # Commit order, items, stock, and outbox together
        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "order_id": order_id,
        "status": "placed",
        "total": str(total)
    }






@app.get("/orders")
def orders(db: DB, user: CurrentUser):
    rows = db.scalars(select(Order).where(Order.user_id == user.id)
                      .order_by(Order.id.desc()).limit(25)).all()
    return [{"id": o.id, "customer_name": o.customer_name, "total": str(o.total),
             "status": o.status, "created_at": o.created_at.isoformat()} for o in rows]
