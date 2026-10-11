
import sqlite3
from pathlib import Path


# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "smart_retail.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)

    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON")

    # Return rows like dictionaries
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# CREATE TABLES
# ============================================================

def create_tables():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.executescript("""

    -- ======================================================
    -- PRODUCTS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS products (

        id TEXT PRIMARY KEY,

        name TEXT NOT NULL,

        category TEXT,

        rfid_tag TEXT UNIQUE,

        price REAL NOT NULL DEFAULT 0,

        purchase_price REAL DEFAULT 0,

        unit_weight REAL,

        current_stock INTEGER NOT NULL DEFAULT 0,

        minimum_stock INTEGER NOT NULL DEFAULT 0,

        supplier TEXT,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );


    -- ======================================================
    -- TROLLEYS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS trolleys (

        id TEXT PRIMARY KEY,

        trolley_number TEXT UNIQUE NOT NULL,

        status TEXT NOT NULL DEFAULT 'available',

        firmware_version TEXT,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

        CHECK (
            status IN (
                'available',
                'shopping',
                'alert',
                'checkout',
                'offline'
            )
        )
    );


    -- ======================================================
    -- CART ITEMS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS cart_items (

        id TEXT PRIMARY KEY,

        trolley_id TEXT NOT NULL,

        product_id TEXT NOT NULL,

        quantity INTEGER NOT NULL DEFAULT 1,

        expected_weight REAL,

        actual_weight REAL,

        verified INTEGER NOT NULL DEFAULT 0,

        added_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (trolley_id)
            REFERENCES trolleys(id)
            ON DELETE CASCADE,

        FOREIGN KEY (product_id)
            REFERENCES products(id)
    );


    -- ======================================================
    -- TRANSACTIONS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS transactions (

        id TEXT PRIMARY KEY,

        trolley_id TEXT NOT NULL,

        total_amount REAL NOT NULL DEFAULT 0,

        payment_status TEXT,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (trolley_id)
            REFERENCES trolleys(id)
    );


    -- ======================================================
    -- TRANSACTION ITEMS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS transaction_items (

        id TEXT PRIMARY KEY,

        transaction_id TEXT NOT NULL,

        product_id TEXT NOT NULL,

        quantity INTEGER NOT NULL DEFAULT 1,

        unit_price REAL NOT NULL DEFAULT 0,

        total_price REAL NOT NULL DEFAULT 0,

        FOREIGN KEY (transaction_id)
            REFERENCES transactions(id)
            ON DELETE CASCADE,

        FOREIGN KEY (product_id)
            REFERENCES products(id)
    );


    -- ======================================================
    -- STOCK ORDERS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS stock_orders (

        id TEXT PRIMARY KEY,

        supplier TEXT,

        order_date TEXT,

        expected_date TEXT,

        notes TEXT,

        status TEXT NOT NULL DEFAULT 'pending',

        CHECK (
            status IN (
                'pending',
                'partially_received',
                'received'
            )
        )
    );


    -- ======================================================
    -- STOCK ORDER ITEMS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS stock_order_items (

        id TEXT PRIMARY KEY,

        order_id TEXT NOT NULL,

        product_id TEXT NOT NULL,

        quantity_ordered INTEGER NOT NULL DEFAULT 0,

        quantity_received INTEGER NOT NULL DEFAULT 0,

        purchase_price REAL DEFAULT 0,

        FOREIGN KEY (order_id)
            REFERENCES stock_orders(id)
            ON DELETE CASCADE,

        FOREIGN KEY (product_id)
            REFERENCES products(id)
    );


    -- ======================================================
    -- INVENTORY MOVEMENTS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS inventory_movements (

        id TEXT PRIMARY KEY,

        product_id TEXT NOT NULL,

        type TEXT NOT NULL,

        quantity INTEGER NOT NULL,

        reference_id TEXT,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        CHECK (
            type IN (
                'SALE',
                'PURCHASE',
                'ADJUSTMENT',
                'DISCREPANCY'
            )
        ),

        FOREIGN KEY (product_id)
            REFERENCES products(id)
    );


    -- ======================================================
    -- ALERTS
    -- ======================================================

    CREATE TABLE IF NOT EXISTS alerts (

        id TEXT PRIMARY KEY,

        trolley_id TEXT,

        product_id TEXT,

        type TEXT,

        expected_value REAL,

        actual_value REAL,

        status TEXT NOT NULL DEFAULT 'active',

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        resolved_at TEXT,

        FOREIGN KEY (trolley_id)
            REFERENCES trolleys(id),

        FOREIGN KEY (product_id)
            REFERENCES products(id)
    );


    -- ======================================================
    -- INDEXES
    -- ======================================================

    CREATE INDEX IF NOT EXISTS idx_products_rfid
        ON products(rfid_tag);

    CREATE INDEX IF NOT EXISTS idx_cart_trolley
        ON cart_items(trolley_id);

    CREATE INDEX IF NOT EXISTS idx_cart_product
        ON cart_items(product_id);

    CREATE INDEX IF NOT EXISTS idx_alerts_trolley
        ON alerts(trolley_id);

    CREATE INDEX IF NOT EXISTS idx_alerts_status
        ON alerts(status);

    CREATE INDEX IF NOT EXISTS idx_inventory_product
        ON inventory_movements(product_id);

    """)

    conn.commit()
    conn.close()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    create_tables()

    print("====================================")
    print("SQLite database initialized")
    print("Database:", DATABASE_PATH)
    print("All tables created successfully")
    print("====================================")

