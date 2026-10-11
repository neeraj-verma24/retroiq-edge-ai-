import sqlite3
import uuid
import random
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# RETROIQ — SAFE ADDITIVE DEMO DATA SEEDER
#
# IMPORTANT:
# - DOES NOT DELETE existing products, trolleys, transactions,
#   cart items, orders, alerts, or inventory movements.
# - Creates a backup before making changes.
# - Safe to run once for a polished prototype/demo dataset.
# - If the demo seed is already present, it exits without changes.
#
# Run from:
#   backend\
#
#   python seed_demo_data_safe.py
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "smart_retail.db"
BACKUP_PATH = BASE_DIR.parent / "smart_retail_before_demo_seed.db"

random.seed(26179)

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(IST)

# New products only. Existing products are never modified.
PRODUCTS = [
    ("Saffola Gold Oil 1L", "Cooking Oil", "DEMO-RFID-001", 165, 138, 1.00, 18, 5, "Marico Distributor"),
    ("Kelloggs Corn Flakes 300g", "Breakfast", "DEMO-RFID-002", 195, 150, 0.30, 21, 6, "Kelloggs Distributor"),
    ("Kissan Tomato Ketchup 500g", "Grocery", "DEMO-RFID-003", 125, 96, 0.50, 17, 5, "HUL Distributor"),
    ("Yippee Magic Masala 70g", "Instant Food", "DEMO-RFID-004", 15, 11, 0.07, 26, 8, "ITC Foods"),
    ("Bingo Mad Angles 90g", "Snacks", "DEMO-RFID-005", 25, 17, 0.09, 12, 8, "ITC Snacks"),
    ("Sprite 750ml", "Beverages", "DEMO-RFID-006", 45, 35, 0.75, 7, 8, "Coca-Cola Distributor"),
    ("Bru Instant Coffee 100g", "Beverages", "DEMO-RFID-007", 155, 125, 0.10, 20, 6, "HUL Distributor"),
    ("Head & Shoulders Shampoo 180ml", "Personal Care", "DEMO-RFID-008", 245, 185, 0.18, 31, 8, "P&G Distributor"),
    ("Pears Bath Soap 100g", "Personal Care", "DEMO-RFID-009", 58, 42, 0.10, 27, 8, "HUL Distributor"),
    ("Ariel Matic Powder 2kg", "Household", "DEMO-RFID-010", 340, 285, 2.00, 18, 5, "P&G Home Care"),
    ("Pril Dishwash Liquid 750ml", "Household", "DEMO-RFID-011", 145, 112, 0.75, 23, 6, "HENKEL Distributor"),
    ("Domex Toilet Cleaner 1L", "Household", "DEMO-RFID-012", 185, 145, 1.00, 4, 6, "HUL Home Care"),
    ("Stayfree Ultra 20 Pads", "Hygiene", "DEMO-RFID-013", 175, 138, 0.20, 14, 6, "Johnson Distributor"),
    ("Navneet Notebook A4", "Stationery", "DEMO-RFID-014", 75, 50, 0.35, 29, 8, "Navneet Distributor"),
    ("Wipro LED Bulb 9W", "Home Utility", "DEMO-RFID-015", 135, 98, 0.05, 17, 5, "Wipro Distributor"),
    ("Soan Papdi 250g", "Sweets", "DEMO-RFID-016", 145, 105, 0.25, 13, 5, "Haldiram Distributor"),
]

# Basket patterns make Shopper Analytics produce meaningful co-purchase pairs.
BASKETS = [
    (["Saffola Gold Oil 1L", "Kelloggs Corn Flakes 300g", "Kissan Tomato Ketchup 500g"], 12),
    (["Yippee Magic Masala 70g", "Bingo Mad Angles 90g", "Sprite 750ml"], 15),
    (["Head & Shoulders Shampoo 180ml", "Pears Bath Soap 100g"], 10),
    (["Ariel Matic Powder 2kg", "Pril Dishwash Liquid 750ml"], 8),
    (["Bru Instant Coffee 100g", "Bingo Mad Angles 90g"], 8),
    (["Navneet Notebook A4", "Wipro LED Bulb 9W"], 4),
    (["Soan Papdi 250g", "Bru Instant Coffee 100g"], 5),
    (["Stayfree Ultra 20 Pads", "Head & Shoulders Shampoo 180ml"], 4),
]

def new_id():
    return str(uuid.uuid4())

def iso(dt):
    return dt.isoformat()

def table_exists(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None

def id_value(conn, table):
    """
    Works with either INTEGER or TEXT/UUID primary-key schemas.
    """
    info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    row = next((r for r in info if r[1] == "id"), None)
    declared = (row[2] if row else "").upper()

    if row and row[5] and "INT" in declared:
        return conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()[0]

    return new_id()

def ensure_backup():
    if not BACKUP_PATH.exists():
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print("Backup created:", BACKUP_PATH)

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    required = [
        "products",
        "trolleys",
        "transactions",
        "transaction_items",
        "inventory_movements",
        "stock_orders",
        "stock_order_items",
        "alerts",
    ]

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        missing = [t for t in required if not table_exists(conn, t)]
        if missing:
            raise RuntimeError(f"Missing database tables: {', '.join(missing)}")

        # Idempotency sentinel.
        already = conn.execute(
            "SELECT id FROM products WHERE rfid_tag = 'DEMO-RFID-001' LIMIT 1"
        ).fetchone()

        if already:
            print("Demo seed already exists. No changes made.")
            return

        ensure_backup()

        # --------------------------------------------------------
        # 1. PRODUCTS
        # --------------------------------------------------------
        product_map = {}

        for name, category, rfid, price, buy, weight, stock, minimum, supplier in PRODUCTS:
            pid = id_value(conn, "products")
            product_map[name] = {
                "id": pid,
                "price": price,
                "buy": buy,
                "weight": weight,
            }

            conn.execute(
                """
                INSERT INTO products
                (id, name, category, rfid_tag, price, purchase_price,
                 unit_weight, current_stock, minimum_stock, supplier,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid, name, category, rfid, price, buy, weight,
                    stock, minimum, supplier,
                    iso(NOW - timedelta(days=45)),
                    iso(NOW),
                ),
            )

        # --------------------------------------------------------
        # 2. EXTRA TROLLEYS
        # --------------------------------------------------------
        trolley_map = {}

        for number, status in [
            ("Cart 06", "shopping"),
            ("Cart 07", "available"),
            ("Cart 08", "shopping"),
            ("Cart 09", "alert"),
            ("Cart 10", "checkout"),
        ]:
            existing = conn.execute(
                "SELECT id FROM trolleys WHERE trolley_number = ?",
                (number,),
            ).fetchone()

            if existing:
                trolley_map[number] = existing[0]
                continue

            tid = id_value(conn, "trolleys")
            trolley_map[number] = tid

            conn.execute(
                """
                INSERT INTO trolleys
                (id, trolley_number, status, firmware_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tid,
                    number,
                    status,
                    "v1.4.2",
                    iso(NOW - timedelta(days=20)),
                    iso(NOW),
                ),
            )

        # --------------------------------------------------------
        # 3. 45 PAID TRANSACTIONS
        # --------------------------------------------------------
        product_names = list(product_map.keys())
        sold = {name: 0 for name in product_names}

        for i in range(45):
            created = NOW - timedelta(
                days=random.randint(0, 29),
                hours=random.randint(0, 10),
                minutes=random.randint(0, 59),
            )

            trolley_number = f"Cart {6 + (i % 5):02d}"
            trolley_id = trolley_map[trolley_number]

            basket = random.choices(
                BASKETS,
                weights=[x[1] for x in BASKETS],
                k=1,
            )[0][0]

            names = list(dict.fromkeys(basket))

            # Sometimes add one extra product.
            if random.random() < 0.35:
                extra = random.choice(product_names)
                if extra not in names:
                    names.append(extra)

            transaction_id = id_value(conn, "transactions")
            total = 0.0
            item_rows = []

            for name in names:
                p = product_map[name]
                qty = random.choices([1, 2, 3], weights=[78, 18, 4], k=1)[0]
                line_total = round(p["price"] * qty, 2)
                total += line_total
                sold[name] += qty

                item_rows.append((name, qty, p["price"], line_total))

            conn.execute(
                """
                INSERT INTO transactions
                (id, trolley_id, total_amount, payment_status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    trolley_id,
                    round(total, 2),
                    "paid",
                    iso(created),
                ),
            )

            for name, qty, unit_price, line_total in item_rows:
                p = product_map[name]

                conn.execute(
                    """
                    INSERT INTO transaction_items
                    (id, transaction_id, product_id, quantity,
                     unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_value(conn, "transaction_items"),
                        transaction_id,
                        p["id"],
                        qty,
                        unit_price,
                        line_total,
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO inventory_movements
                    (id, product_id, type, quantity, reference_id,
                     created_at, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_value(conn, "inventory_movements"),
                        p["id"],
                        "SALE",
                        qty,
                        transaction_id,
                        iso(created),
                        "RETROIQ demo sale",
                    ),
                )

        # Keep demo product stock positive and consistent with demo sales.
        for name, sold_qty in sold.items():
            p = product_map[name]
            row = conn.execute(
                "SELECT current_stock FROM products WHERE id = ?",
                (p["id"],),
            ).fetchone()

            new_stock = max(0, row[0] - sold_qty)

            conn.execute(
                """
                UPDATE products
                SET current_stock = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_stock, iso(NOW), p["id"]),
            )

        # --------------------------------------------------------
        # 4. LIVE CART ITEMS
        # --------------------------------------------------------
        def add_cart(trolley_number, name, qty, verified=True, mismatch=False):
            tid = trolley_map[trolley_number]
            p = product_map[name]
            expected = round(p["weight"] * qty, 3)
            actual = round(expected * (1.18 if mismatch else 1.0), 3)

            conn.execute(
                """
                INSERT INTO cart_items
                (id, trolley_id, product_id, quantity,
                 expected_weight, actual_weight, verified, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_value(conn, "cart_items"),
                    tid,
                    p["id"],
                    qty,
                    expected,
                    actual,
                    1 if verified else 0,
                    iso(NOW - timedelta(minutes=random.randint(2, 25))),
                ),
            )

        add_cart("Cart 06", "Yippee Magic Masala 70g", 2)
        add_cart("Cart 06", "Bingo Mad Angles 90g", 1)
        add_cart("Cart 06", "Sprite 750ml", 1)

        add_cart("Cart 08", "Saffola Gold Oil 1L", 1)
        add_cart("Cart 08", "Kelloggs Corn Flakes 300g", 1)
        add_cart("Cart 08", "Kissan Tomato Ketchup 500g", 1)

        add_cart("Cart 09", "Head & Shoulders Shampoo 180ml", 1, verified=False, mismatch=True)

        # --------------------------------------------------------
        # 5. GUARDIAN ALERTS
        # --------------------------------------------------------
        alert_specs = [
            ("Cart 09", "Head & Shoulders Shampoo 180ml", "weight_mismatch", 0.18, 0.21, "active"),
            ("Cart 06", "Yippee Magic Masala 70g", "weight_mismatch", 0.14, 0.18, "resolved"),
            ("Cart 08", None, "unregistered_item", None, "RFID-UNKNOWN-501", "active"),
            ("Cart 07", "Sprite 750ml", "weight_mismatch", 0.75, 0.61, "resolved"),
            ("Cart 10", None, "unregistered_item", None, "RFID-UNKNOWN-774", "active"),
            ("Cart 06", "Bingo Mad Angles 90g", "inventory_discrepancy", 0.09, 0.13, "resolved"),
        ]

        for i, (cart, name, alert_type, expected, actual, status) in enumerate(alert_specs):
            product_id = product_map[name]["id"] if name else None
            created = NOW - timedelta(hours=i * 6 + 1)

            conn.execute(
                """
                INSERT INTO alerts
                (id, trolley_id, product_id, type, expected_value,
                 actual_value, status, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_value(conn, "alerts"),
                    trolley_map[cart],
                    product_id,
                    alert_type,
                    expected,
                    actual,
                    status,
                    iso(created),
                    iso(created + timedelta(minutes=8))
                    if status == "resolved" else None,
                ),
            )

        # --------------------------------------------------------
        # 6. STOCK ORDERS
        # --------------------------------------------------------
        orders = [
            ("Marico Distributor", "Saffola Gold Oil 1L", 40, 0, "pending"),
            ("ITC Foods", "Yippee Magic Masala 70g", 60, 30, "partially_received"),
            ("ITC Snacks", "Bingo Mad Angles 90g", 40, 20, "partially_received"),
            ("Coca-Cola Distributor", "Sprite 750ml", 30, 30, "received"),
            ("P&G Distributor", "Head & Shoulders Shampoo 180ml", 25, 10, "partially_received"),
            ("P&G Home Care", "Ariel Matic Powder 2kg", 25, 25, "received"),
            ("Haldiram Distributor", "Soan Papdi 250g", 20, 20, "received"),
        ]

        for i, (supplier, name, ordered, received, status) in enumerate(orders):
            order_id = id_value(conn, "stock_orders")
            order_date = NOW - timedelta(days=i + 1)
            expected_date = (NOW + timedelta(days=i + 2)).date().isoformat()
            p = product_map[name]

            conn.execute(
                """
                INSERT INTO stock_orders
                (id, supplier, order_date, expected_date, notes,
                 status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    supplier,
                    order_date.date().isoformat(),
                    expected_date,
                    "RETROIQ demo replenishment",
                    status,
                    iso(order_date),
                    iso(NOW),
                ),
            )

            conn.execute(
                """
                INSERT INTO stock_order_items
                (id, order_id, product_id, quantity_ordered,
                 quantity_received, purchase_price)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    id_value(conn, "stock_order_items"),
                    order_id,
                    p["id"],
                    ordered,
                    received,
                    p["buy"],
                ),
            )

        # --------------------------------------------------------
        # 7. AI EVENTS
        # --------------------------------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                session_id TEXT,
                trolley_id TEXT,
                zone_id TEXT,
                value REAL,
                metadata_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        zones = ["entrance", "dairy", "snacks", "personal-care", "checkout"]

        for i in range(70):
            created = NOW - timedelta(minutes=random.randint(5, 60 * 24 * 14))
            session_id = f"demo-session-{i // 2 + 1:03d}"
            trolley_number = f"Cart {6 + (i % 5):02d}"

            if i % 7 == 0:
                event_type = "zone_enter"
                zone_id = zones[i % len(zones)]
                value = 1.0
            elif i % 7 == 1:
                event_type = "zone_exit"
                zone_id = zones[i % len(zones)]
                value = float(random.randint(20, 180))
            elif i % 5 == 0:
                event_type = "queue_count"
                zone_id = "checkout"
                value = float(random.randint(2, 9))
            else:
                event_type = "shopper_session"
                zone_id = None
                value = float(random.randint(1, 5))

            conn.execute(
                """
                INSERT INTO ai_events
                (id, event_type, session_id, trolley_id, zone_id,
                 value, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id(),
                    event_type,
                    session_id,
                    trolley_map[trolley_number],
                    zone_id,
                    value,
                    '{"source":"demo_seed","synthetic":true}',
                    iso(created),
                ),
            )

        conn.commit()

        # --------------------------------------------------------
        # 8. SUMMARY
        # --------------------------------------------------------
        print()
        print("========================================")
        print("RETROIQ SAFE DEMO DATA SEEDED")
        print("========================================")

        for table in [
            "products",
            "trolleys",
            "cart_items",
            "transactions",
            "transaction_items",
            "stock_orders",
            "stock_order_items",
            "inventory_movements",
            "alerts",
            "ai_events",
        ]:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            print(f"{table:24} {count}")

        print("========================================")
        print("Backup:", BACKUP_PATH)
        print("Database:", DB_PATH)
        print("========================================")
        print("Existing data was NOT deleted.")

    except Exception:
        conn.rollback()
        print("SEED FAILED — database changes were rolled back.")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    main()
