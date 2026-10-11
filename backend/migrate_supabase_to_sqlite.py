import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import os


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "smart_retail.db"

ENV_PATH = Path(__file__).resolve().parent / ".env"

load_dotenv(ENV_PATH)


# ============================================================
# SUPABASE CONNECTION
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing from backend/.env")

if not SUPABASE_SECRET_KEY:
    raise Exception("SUPABASE_SECRET_KEY missing from backend/.env")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# ============================================================
# SQLITE CONNECTION
# ============================================================

conn = sqlite3.connect(DATABASE_PATH)

conn.execute("PRAGMA foreign_keys = OFF")

cursor = conn.cursor()


# ============================================================
# TABLE ORDER
# ============================================================

tables = [
    "products",
    "trolleys",
    "stock_orders",
    "stock_order_items",
    "cart_items",
    "transactions",
    "transaction_items",
    "inventory_movements",
    "alerts"
]


# ============================================================
# SQLITE TYPE DETECTION
# ============================================================

def detect_sqlite_type(rows, column):

    for row in rows:

        value = row.get(column)

        if value is None:
            continue

        if isinstance(value, bool):
            return "INTEGER"

        if isinstance(value, int):
            return "INTEGER"

        if isinstance(value, float):
            return "REAL"

        return "TEXT"

    return "TEXT"


# ============================================================
# GET EXISTING SQLITE COLUMNS
# ============================================================

def get_sqlite_columns(table):

    result = cursor.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return {
        row[1]
        for row in result
    }


# ============================================================
# ADD MISSING COLUMNS
# ============================================================

def add_missing_columns(table, rows):

    if not rows:
        return

    existing_columns = get_sqlite_columns(table)

    supabase_columns = list(rows[0].keys())

    for column in supabase_columns:

        if column in existing_columns:
            continue

        column_type = detect_sqlite_type(
            rows,
            column
        )

        print(
            f"  Adding missing column: "
            f"{column} ({column_type})"
        )

        cursor.execute(
            f'''
            ALTER TABLE "{table}"
            ADD COLUMN "{column}" {column_type}
            '''
        )

    conn.commit()


# ============================================================
# MIGRATION
# ============================================================

print()
print("==============================================")
print(" SUPABASE → SQLITE MIGRATION")
print("==============================================")
print()


for table in tables:

    print(f"Migrating: {table}")

    # --------------------------------------------------------
    # READ FROM SUPABASE
    # --------------------------------------------------------

    response = (
        supabase
        .table(table)
        .select("*")
        .execute()
    )

    rows = response.data or []

    print(
        f"  Supabase rows: {len(rows)}"
    )

    if not rows:

        print("  Nothing to migrate.")
        print()

        continue


    # --------------------------------------------------------
    # ADD ANY MISSING COLUMNS
    # --------------------------------------------------------

    add_missing_columns(
        table,
        rows
    )


    # --------------------------------------------------------
    # GET COLUMNS
    # --------------------------------------------------------

    columns = list(rows[0].keys())

    column_names = ", ".join(
        f'"{column}"'
        for column in columns
    )

    placeholders = ", ".join(
        "?"
        for _ in columns
    )


    # --------------------------------------------------------
    # INSERT / REPLACE
    # --------------------------------------------------------

    sql = f"""
        INSERT OR REPLACE INTO "{table}"
        ({column_names})
        VALUES ({placeholders})
    """


    values = []

    for row in rows:

        values.append(
            [
                row.get(column)
                for column in columns
            ]
        )


    cursor.executemany(
        sql,
        values
    )

    conn.commit()


    print(
        f"  SQLite rows inserted: {len(rows)}"
    )

    print()


# ============================================================
# RE-ENABLE FOREIGN KEYS
# ============================================================

conn.execute(
    "PRAGMA foreign_keys = ON"
)


# ============================================================
# VERIFICATION
# ============================================================

print("==============================================")
print(" MIGRATION VERIFICATION")
print("==============================================")

for table in tables:

    result = cursor.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()

    count = result[0]

    print(
        f"{table:25} {count} rows"
    )


# ============================================================
# CLOSE
# ============================================================

conn.close()


print()
print("==============================================")
print(" MIGRATION COMPLETED")
print("==============================================")