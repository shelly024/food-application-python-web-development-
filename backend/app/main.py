from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from db import get_db, row_to_dict
import urllib.error #should delete?
import urllib.request  #should delete?
from typing import Annotated
import os, json
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import OpenAI


app = FastAPI(title="Delivery App API") #start a backend server

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    candidate = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(candidate, expected)


def init_db():
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                token TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                rating REAL NOT NULL,
                delivery_minutes INTEGER NOT NULL,
                delivery_fee REAL NOT NULL,
                minimum_order REAL NOT NULL,
                hero_image TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                image TEXT NOT NULL,
                category TEXT NOT NULL,
                popular INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (store_id) REFERENCES stores(id) --there's 2 store_id?
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL,
                payment_status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                food_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (food_id) REFERENCES foods(id)
            );
            """
        )

        existing = db.execute("SELECT COUNT(*) AS count FROM stores").fetchone()["count"]
        if existing:
            return

        stores = [
            (
                "Luna Verde",
                "Modern Italian",
                4.8,
                24,
                1.99,
                12,
                "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=1200&q=80",
                "Handmade pasta, crisp salads, and slow-cooked sauces from a bright neighborhood kitchen.",
            ),
            (
                "Tokyo Bowl House",
                "Japanese",
                4.7,
                18,
                0.99,
                10,
                "https://images.unsplash.com/photo-1617196034796-73dfa7b1fd56?auto=format&fit=crop&w=1200&q=80",
                "Fresh rice bowls, yakitori, and clean flavors built for fast comfort.",
            ),
            (
                "The Daily Grill",
                "Burgers",
                4.6,
                21,
                1.49,
                9,
                "https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=1200&q=80",
                "Charred burgers, loaded fries, and proper sauces made after each order.",
            ),
        ]
        db.executemany(
            """
            INSERT INTO stores
                (name, cuisine, rating, delivery_minutes, delivery_fee, minimum_order, hero_image, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            stores,
        )

        foods = [
            (1, "Truffle Tagliatelle", "Egg pasta, wild mushrooms, parmesan, black truffle oil.", 15.5, "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?auto=format&fit=crop&w=900&q=80", "Pasta", 1),
            (1, "Burrata Pomodoro", "Creamy burrata with cherry tomatoes, basil, olive oil.", 10.25, "https://images.unsplash.com/photo-1505253716362-afaea1d3d1af?auto=format&fit=crop&w=900&q=80", "Starters", 1),
            (1, "Tiramisu Cup", "Mascarpone cream, espresso-soaked sponge, cocoa.", 6.5, "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=900&q=80", "Dessert", 0),
            (2, "Salmon Teriyaki Bowl", "Grilled salmon, steamed rice, pickled cucumber, sesame.", 13.75, "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=900&q=80", "Bowls", 1),
            (2, "Chicken Katsu Curry", "Crispy chicken, curry sauce, rice, red ginger.", 12.95, "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=900&q=80", "Hot Plates", 1),
            (2, "Miso Aubergine", "Roasted aubergine with sweet miso glaze and scallions.", 8.5, "https://images.unsplash.com/photo-1498654896293-37aacf113fd9?auto=format&fit=crop&w=900&q=80", "Small Plates", 0),
            (3, "House Smash Burger", "Double beef patty, cheddar, pickles, house sauce.", 11.95, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80", "Burgers", 1),
            (3, "Crispy Halloumi Burger", "Halloumi, slaw, chilli jam, garlic mayo.", 10.95, "https://images.unsplash.com/photo-1550317138-10000687a72b?auto=format&fit=crop&w=900&q=80", "Burgers", 0),
            (3, "Rosemary Fries", "Skin-on fries with rosemary salt and aioli.", 4.75, "https://images.unsplash.com/photo-1576107232684-1279f390859f?auto=format&fit=crop&w=900&q=80", "Sides", 1),
        ]
        db.executemany(
            """
            INSERT INTO foods
                (store_id, name, description, price, image, category, popular)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            foods,
        )


@app.on_event("startup")
def startup():
    init_db()


class RegisterPayload(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginPayload(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str


class OrderItemPayload(BaseModel):
    food_id: int
    quantity: int = Field(gt=0, le=20)

class OrderPayload(BaseModel):
    items: list[OrderItemPayload] = Field(min_length=1)

class SearchInput(BaseModel):
    user_input: str
class FoodRecommendation(BaseModel):
    food_id:int
    food_name:str
    food_recommend_reason:str
    food_price:float
    food_image:str

class StoreRecommendation(BaseModel):
    store_id:int
    store_name:str
    store_recommend_reason:str
    store_image:str
    rating:float
    delivery_minute:int
    foodlist: list[FoodRecommendation]

class StoresList(BaseModel):
    stores_recommend: list[StoreRecommendation]

def issue_user_response(user: sqlite3.Row):
    return {
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
        "token": user["token"],
    }


def current_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    token = authorization.removeprefix("Bearer ").strip()
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")
    return user


@app.post("/api/auth/register")
def register(payload: RegisterPayload):
    if "@" not in payload.email:
        raise HTTPException(status_code=422, detail="Please enter a valid email")
    token = secrets.token_urlsafe(32)
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO users (name, email, password_hash, token) VALUES (?, ?, ?, ?)",
                (payload.name, payload.email.lower(), hash_password(payload.password), token),
            )
            user = db.execute("SELECT * FROM users WHERE email = ?", (payload.email.lower(),)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email is already registered") from None
    return issue_user_response(user)


@app.post("/api/auth/login")   # it can use JWT no need to check database?
def login(payload: LoginPayload):
    if "@" not in payload.email:
        raise HTTPException(status_code=422, detail="Please enter a valid email")
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (payload.email.lower(),)).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = secrets.token_urlsafe(32)
        db.execute("UPDATE users SET token = ? WHERE id = ?", (token, user["id"]))
        user = db.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return issue_user_response(user)


@app.get("/api/stores")
def list_stores():
    with get_db() as db:
        stores = db.execute("SELECT * FROM stores ORDER BY rating DESC").fetchall()
    return [row_to_dict(store) for store in stores]


@app.get("/api/stores/{store_id}")
def get_store(store_id: int):
    with get_db() as db:
        store = db.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        foods = db.execute("SELECT * FROM foods WHERE store_id = ? ORDER BY popular DESC, id", (store_id,)).fetchall()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    data = row_to_dict(store)
    data["foods"] = [row_to_dict(food) for food in foods]
    return data


@app.post("/api/orders")
def create_order(payload: OrderPayload, user: sqlite3.Row = Depends(current_user)):
    ids = [item.food_id for item in payload.items]
    placeholders = ",".join("?" for _ in ids)
    with get_db() as db:
        foods = db.execute(f"SELECT * FROM foods WHERE id IN ({placeholders})", ids).fetchall()
        food_by_id = {food["id"]: food for food in foods}
        if len(food_by_id) != len(set(ids)):
            raise HTTPException(status_code=400, detail="One or more food items do not exist")

        total = sum(food_by_id[item.food_id]["price"] * item.quantity for item in payload.items)
        cursor = db.execute(
            "INSERT INTO orders (user_id, total, status, payment_status) VALUES (?, ?, ?, ?)",
            (user["id"], round(total, 2), "created", "pending"),
        )
        order_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO order_items (order_id, food_id, quantity, price) VALUES (?, ?, ?, ?)",
            [
                (order_id, item.food_id, item.quantity, food_by_id[item.food_id]["price"])
                for item in payload.items
            ],
        )
    return {"order_id": order_id, "total": round(total, 2), "status": "created", "payment_status": "pending"}

@app.post("/api/recommendations")
def search_recommendations(payload:SearchInput):
    query = payload.user_input
    with get_db() as db:
        result1 = db.execute("SELECT * FROM stores ORDER BY id ASC").fetchall()
        result2 = db.execute("SELECT * FROM foods ORDER BY store_id ASC").fetchall()

    stores = [row_to_dict(row) for row in result1]
    foods = [row_to_dict(row) for row in result2]

    store_lookup = {}
    for store in stores:
        store['foods'] = []
        store_lookup[store['id']] = store
    for food in foods:
        store_lookup[food['store_id']]['foods'].append(food)
    data = list(store_lookup.values())

    response = client.chat.completions.parse(
        model="gemini-3.5-flash",
        messages=[
            {"role": "user",
             "content": query + json.dumps(data) + "at most recommend 3 stores and at most 3 types of foods per store"
             }
        ],
        response_format=StoresList,
    )

    result = response.choices[0].message.parsed
    result.stores_recommend = result.stores_recommend[:3]
    for r in result.stores_recommend:
        r.foodlist = r.foodlist[:3]
    return result.stores_recommend


@app.get("/api/health")
def health():
    return {"ok": True}
