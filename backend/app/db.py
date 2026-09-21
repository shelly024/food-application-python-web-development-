from pathlib import Path
import sqlite3
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "delivery.db"

@contextmanager
def get_db():   #how to handle error
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def row_to_dict(row: sqlite3.Row | None):
    return dict(row) if row else None

def init_db():
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
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
                FOREIGN KEY (store_id) REFERENCES stores(id) 
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