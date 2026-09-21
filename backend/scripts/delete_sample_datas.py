from app.db import get_db, row_to_dict

with get_db() as db:
    db.execute("DELETE FROM order_items")
    db.execute("DELETE FROM orders")
    db.execute("DELETE FROM users")

with get_db() as d:
    querys = d.execute("SELECT * FROM users").fetchall()
    query = [row_to_dict(item) for item in querys]
    print(query)