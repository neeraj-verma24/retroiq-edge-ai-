from fastapi import FastAPI, HTTPException, Body, Request
from database import get_connection
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import os
import json
import paho.mqtt.client as mqtt
import uuid
import razorpay
import hmac
import requests
import hashlib
from datetime import datetime, timezone

from ai_engine import (
    control_room,
    inventory_intelligence,
    revenue_leak_radar,
    shopper_intelligence,
    queue_intelligence,
)




# =========================
# LOAD ENVIRONMENT
# =========================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)






# =========================
# FASTAPI APP
# =========================

app = FastAPI(
    title="Smart Retail Edge Server",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5175",
        "http://localhost:5174",
        "https://retroiq-flame.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# AI RUNTIME / LOCAL EDGE STATE
# =========================================================

def ensure_ai_schema():
    """
    Ensure the local SQLite database has the AI event table.
    This keeps AI features fully local/offline-capable.
    """
    conn = get_connection()
    try:
        conn.execute("""
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
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_events_type_time
            ON ai_events(event_type, created_at)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_events_session
            ON ai_events(session_id)
        """)

        conn.commit()

    finally:
        conn.close()


ensure_ai_schema()

# =========================
# MQTT CONFIGURATION
# =========================

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "cart/+/scan"


def on_connect(client, userdata, flags, reason_code, properties):

    print("MQTT connected successfully")

    # Subscribe to RFID scan messages
    client.subscribe("cart/+/scan")
    print("Subscribed to: cart/+/scan")

    # Subscribe to weight messages
    client.subscribe("cart/+/weight")
    print("Subscribed to: cart/+/weight")

    # Subscribe to cart status messages
    client.subscribe("cart/+/status")
    print("Subscribed to: cart/+/status")

def on_message(client, userdata, msg):
    try:
        # Get raw MQTT message
        raw_message = msg.payload.decode()

        print("\n========== MQTT MESSAGE ==========")
        print("Topic:", msg.topic)
        print("Raw Message:", raw_message)

        # Convert JSON to Python dictionary
        payload = json.loads(raw_message)

        print("Payload:", payload)

        # Get cart number
        topic_parts = msg.topic.split("/")

        if len(topic_parts) < 3:
            print("Invalid MQTT topic:", msg.topic)
            return

        cart_id = topic_parts[1]
        message_type = topic_parts[2]

        # =========================================================
        # CART STATUS SYNCHRONIZATION
        # Topic: cart/05/status
        # =========================================================

        if message_type == "status":

            status = payload.get("status")

            if not status:
                print("Cart status missing in message")
                return

            print("CART STATUS UPDATE")
            print("Cart:", cart_id)
            print("Status:", status)

            # -----------------------------------------------------
            # Allowed trolley statuses
            # -----------------------------------------------------

            allowed_statuses = [
                "available",
                "shopping",
                "alert",
                "checkout",
                "offline"
            ]

            if status not in allowed_statuses:
                print("Invalid cart status:", status)
                return

            # -----------------------------------------------------
            # Update trolley status in database
            # -----------------------------------------------------

            conn = get_connection()

            cursor = conn.execute("""
                UPDATE trolleys
                SET
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE trolley_number = ?
            """, (
                status,
                f"Cart {cart_id}"
            ))

            conn.commit()

            trolley_updated = cursor.rowcount > 0

            conn.close()

            if not trolley_updated:
                print("Trolley not found:", cart_id)
                return

            print("Cart status updated successfully")
            print("Cart:", cart_id)
            print("New Status:", status)

            # -----------------------------------------------------
            # Send confirmation through MQTT
            # -----------------------------------------------------

            status_response = {
                "cart_id": cart_id,
                "status": status,
                "message": "Cart status synchronized"
            }

            mqtt_client.publish(
                f"cart/{cart_id}/status_response",
                json.dumps(status_response)
            )

            print("Status confirmation sent")
            print("==================================\n")

            return

        # =========================================================
        # WEIGHT VERIFICATION
        # Topic: cart/05/weight
        # =========================================================

        if message_type == "weight":

            product_id = payload.get("product_id")
            actual_weight = payload.get("actual_weight")
            quantity = payload.get("quantity", 1)

            if not product_id:
                print("Product ID missing in weight message")
                return

            if actual_weight is None:
                print("Actual weight missing in message")
                return

            print("WEIGHT VERIFICATION REQUEST")
            print("Cart:", cart_id)
            print("Product ID:", product_id)
            print("Quantity:", quantity)
            print("Actual Weight:", actual_weight)

            # -----------------------------------------------------
            # Find trolley
            # -----------------------------------------------------

            conn = get_connection()

            trolley = conn.execute("""
                SELECT id
                FROM trolleys
                WHERE trolley_number = ?
            """, (
                f"Cart {cart_id}",
            )).fetchone()

            if not trolley:
                conn.close()

                print("Trolley not found:", cart_id)

                verification_response = {
                    "status": "not_found",
                    "verified": False,
                    "message": "Trolley not found"
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                return

            trolley_id = trolley["id"]

            # -----------------------------------------------------
            # Find product
            # -----------------------------------------------------

            product_row = conn.execute("""
                SELECT *
                FROM products
                WHERE id = ?
            """, (
                product_id,
            )).fetchone()

            if not product_row:
                conn.close()

                print("Product not found:", product_id)

                verification_response = {
                    "status": "not_found",
                    "verified": False,
                    "message": "Product not found"
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                return

            product = dict(product_row)

            # -----------------------------------------------------
            # Validate unit weight
            # -----------------------------------------------------

            if (
                product["unit_weight"] is None
                or float(product["unit_weight"]) <= 0
            ):
                conn.close()

                print("Invalid product unit weight")

                verification_response = {
                    "status": "invalid",
                    "verified": False,
                    "message": "Product unit weight must be greater than 0"
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                return

            # -----------------------------------------------------
            # Calculate expected weight
            # -----------------------------------------------------

            unit_weight = float(product["unit_weight"])
            expected_weight = unit_weight * int(quantity)

            actual_weight = float(actual_weight)

            # -----------------------------------------------------
            # Calculate difference
            # -----------------------------------------------------

            difference_percent = (
                abs(actual_weight - expected_weight)
                / expected_weight
            ) * 100

            # 5% tolerance
            verified = difference_percent <= 5

            print("Expected Weight:", expected_weight)
            print("Actual Weight:", actual_weight)
            print(
                "Difference:",
                round(difference_percent, 2),
                "%"
            )

            # =====================================================
            # VERIFIED
            # =====================================================

            if verified:

                conn.execute("""
                    INSERT INTO cart_items (
                        trolley_id,
                        product_id,
                        quantity,
                        expected_weight,
                        actual_weight,
                        verified
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    trolley_id,
                    product_id,
                    int(quantity),
                    expected_weight,
                    actual_weight,
                    True
                ))

                conn.commit()
                conn.close()

                verification_response = {
                    "status": "verified",
                    "verified": True,
                    "product_id": product_id,
                    "product_name": product["name"],
                    "price": product["price"],
                    "expected_weight": expected_weight,
                    "actual_weight": actual_weight,
                    "difference_percent": round(
                        difference_percent,
                        2
                    )
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                print("WEIGHT VERIFIED")
                print("Verification response sent")

            # =====================================================
            # MISMATCH
            # =====================================================

            else:

                # -------------------------------------------------
                # Create alert in database
                # -------------------------------------------------

                conn.execute("""
                    INSERT INTO alerts (
                        trolley_id,
                        product_id,
                        type,
                        expected_value,
                        actual_value,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    trolley_id,
                    product_id,
                    "weight_mismatch",
                    expected_weight,
                    actual_weight,
                    "active"
                ))

                conn.commit()
                conn.close()

                # -------------------------------------------------
                # Send alert through MQTT
                # -------------------------------------------------

                alert_message = {
                    "type": "weight_mismatch",
                    "product_id": product_id,
                    "expected_weight": expected_weight,
                    "actual_weight": actual_weight,
                    "difference_percent": round(
                        difference_percent,
                        2
                    ),
                    "message": "Weight mismatch. Verification required.",
                    "status": "active"
                }

                alert_topic = f"cart/{cart_id}/alert"

                mqtt_client.publish(
                    alert_topic,
                    json.dumps(alert_message)
                )

                print("MQTT alert sent")
                print("Alert Topic:", alert_topic)
                print("Alert:", alert_message)

                # -------------------------------------------------
                # Send verification response
                # -------------------------------------------------

                verification_response = {
                    "status": "mismatch",
                    "verified": False,
                    "product_id": product_id,
                    "product_name": product["name"],
                    "expected_weight": expected_weight,
                    "actual_weight": actual_weight,
                    "difference_percent": round(
                        difference_percent,
                        2
                    ),
                    "message": "Weight mismatch. Verification required."
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                print("WEIGHT MISMATCH")
                print("Alert created")
                print("Verification response sent")

            print("==================================\n")
            return

        # =========================================================
        # RFID SCAN
        # Topic: cart/01/scan
        # =========================================================

        if message_type == "scan":

            # Get RFID
            rfid = payload.get("rfid")

            if not rfid:
                print("RFID missing in message")
                return

            print("RFID SCAN")
            print("RFID:", rfid)
            print("Cart:", cart_id)

            # -----------------------------------------------------
            # Search product
            # -----------------------------------------------------

            conn = get_connection()

            product_row = conn.execute("""
                SELECT *
                FROM products
                WHERE rfid_tag = ?
            """, (
                rfid,
            )).fetchone()

            # -----------------------------------------------------
            # Product found
            # -----------------------------------------------------

            if product_row:

                product = dict(product_row)

                print("RFID MATCH FOUND")
                print("Product:", product["name"])
                print("Price:", product["price"])
                print("Weight:", product["unit_weight"])

                trolley = conn.execute("""
                    SELECT id
                    FROM trolleys
                    WHERE trolley_number = ?
                """, (f"Cart {cart_id}",)).fetchone()

                if not trolley:
                    print("Trolley not found:", cart_id)
                    conn.close()
                    return

                trolley_id = trolley["id"]

                existing_item = conn.execute("""
                    SELECT *
                    FROM cart_items
                    WHERE trolley_id = ? AND product_id = ?
                """, (trolley_id, product["id"])).fetchone()

                if existing_item:
                    new_quantity = int(existing_item["quantity"]) + 1
                    new_expected_weight = float(product["unit_weight"]) * new_quantity

                    # Handle old cart items that may have a NULL ID
                    cart_item_id = existing_item["id"]

                    if not cart_item_id:
                        cart_item_id = str(uuid.uuid4())

                        conn.execute("""
                            UPDATE cart_items
                            SET id = ?,
                                quantity = ?,
                                expected_weight = ?,
                                verified = 0
                            WHERE trolley_id = ?
                            AND product_id = ?
                        """, (
                            cart_item_id,
                            new_quantity,
                            new_expected_weight,
                            trolley_id,
                            product["id"]
                        ))

                        print("Old cart item had NULL ID")
                        print("New Cart Item ID:", cart_item_id)

                    else:
                        conn.execute("""
                            UPDATE cart_items
                            SET quantity = ?,
                                expected_weight = ?,
                                verified = 0
                            WHERE id = ?
                        """, (
                            new_quantity,
                            new_expected_weight,
                            cart_item_id
                        ))

                    print("Existing cart item updated")
                    print("New quantity:", new_quantity)

                else:
                    cart_item_id = str(uuid.uuid4())

                    conn.execute("""
                        INSERT INTO cart_items (
                            id, trolley_id, product_id, quantity,
                            expected_weight, actual_weight, verified
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cart_item_id, trolley_id, product["id"], 1,
                        float(product["unit_weight"]), 0, False
                    ))

                    print("New cart item created")
                    print("Cart Item ID:", cart_item_id)

                conn.commit()

                cart_item = conn.execute("""
                    SELECT * FROM cart_items WHERE id = ?
                """, (cart_item_id,)).fetchone()

                if not cart_item:
                    print("Cart item could not be found after update")
                    conn.close()
                    return

                product_response = {
                    "status": "added",
                    "rfid": rfid,
                    "product_id": product["id"],
                    "cart_item_id": cart_item["id"],
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": cart_item["quantity"],
                    "expected_weight": cart_item["expected_weight"],
                    "verified": False
                }

                response_topic = f"cart/{cart_id}/product"
                mqtt_client.publish(response_topic, json.dumps(product_response))

                print("Product added to cart")
                print("Response Topic:", response_topic)
                print("Response:", product_response)

                conn.close()

            # -----------------------------------------------------
            # Product not found
            # -----------------------------------------------------

            else:

                print("UNREGISTERED RFID DETECTED")
                print("RFID:", rfid)
                print("Cart:", cart_id)

                alert_message = {
                    "type": "unregistered_item",
                    "rfid": rfid,
                    "message": "Unregistered RFID detected",
                    "status": "active"
                }

                alert_topic = f"cart/{cart_id}/alert"

                mqtt_client.publish(
                    alert_topic,
                    json.dumps(alert_message)
                )

                print("Alert sent")
                print("Alert Topic:", alert_topic)

                # -------------------------------------------------
                # Find trolley
                # -------------------------------------------------

                trolley = conn.execute("""
                    SELECT id
                    FROM trolleys
                    WHERE trolley_number = ?
                """, (
                    f"Cart {cart_id}",
                )).fetchone()

                # -------------------------------------------------
                # Save alert
                # -------------------------------------------------

                if trolley:

                    trolley_id = trolley["id"]

                    conn.execute("""
                        INSERT INTO alerts (
                            trolley_id,
                            product_id,
                            type,
                            expected_value,
                            actual_value,
                            status
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        trolley_id,
                        None,
                        "unregistered_item",
                        None,
                        rfid,
                        "active"
                    ))

                    conn.commit()

                    print("Alert saved in database")

                else:
                    print("Trolley not found:", cart_id)

                conn.close()

            print("==================================\n")
            return

        # =========================================================
        # UNKNOWN MQTT MESSAGE TYPE
        # =========================================================

        print("Unknown MQTT message type:", message_type)

    except json.JSONDecodeError as e:

        print("INVALID JSON RECEIVED")
        print("Raw MQTT message:", msg.payload.decode())
        print("JSON error:", e)

    except Exception as e:

        print("MQTT message error:", e)

        

        
mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smart-retail-edge"
)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message        
@app.on_event("startup")
def start_mqtt():
    print("Starting MQTT connection...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()


@app.on_event("shutdown")
def stop_mqtt():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

# =========================
# BASIC ROUTES
# =========================

@app.get("/")
def root():
    return {
        "system": "Smart Retail Intelligence",
        "status": "Edge Server Online"
    }


# =====================================================
# SYSTEM COMPONENT STATUS
# =====================================================
@app.get("/health")
def health():
    return {"status": "healthy"}
@app.get("/system-status")
def system_status():

    # -------------------------------------------------
    # MQTT STATUS
    # -------------------------------------------------

    mqtt_connected = mqtt_client.is_connected()


    # -------------------------------------------------
    # DATABASE STATUS
    # -------------------------------------------------

    database_connected = False

    try:

        conn = get_connection()

        conn.execute("""
            SELECT 1
            FROM products
            LIMIT 1
        """).fetchone()

        conn.close()

        database_connected = True

    except Exception as e:

        print("SQLite database health check failed:", e)


    # -------------------------------------------------
    # FASTAPI STATUS
    # -------------------------------------------------

    fastapi_connected = True


    # -------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------

    return {

        "fastapi": (
            "connected"
            if fastapi_connected
            else "offline"
        ),

        "mqtt": (
            "connected"
            if mqtt_connected
            else "offline"
        ),

        "database": (
            "connected"
            if database_connected
            else "offline"
        )

    } 

# =========================
# PRODUCT DATA MODEL
# =========================

class ProductCreate(BaseModel):
    name: str
    category: str
    rfid_tag: str | None = None
    price: float
    purchase_price: float
    unit_weight: float
    current_stock: int
    minimum_stock: int
    supplier: str
@app.get("/products")
def get_products():
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM products
        ORDER BY name
    """).fetchall()

    conn.close()

    products = [dict(row) for row in rows]

    return {
        "count": len(products),
        "products": products
    }
# =========================
# GET ALL PRODUCTS
# ========================
class PaymentCreate(BaseModel):
    trolley_id: str

class AIEvent(BaseModel):
    event_type: str
    session_id: str | None = None
    trolley_id: str | None = None
    zone_id: str | None = None
    value: float | None = None
    metadata: dict | None = None

@app.post("/products")
def create_product(product: ProductCreate = Body(...)):

    conn = get_connection()

    try:
        product_id = str(uuid.uuid4())

        print("\n========== ADD PRODUCT ==========")
        print("Product received:", product.model_dump())

        cursor = conn.execute("""
            INSERT INTO products (
                id,
                name,
                category,
                rfid_tag,
                price,
                purchase_price,
                unit_weight,
                current_stock,
                minimum_stock,
                supplier
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            product.name,
            product.category,
            product.rfid_tag,
            product.price,
            product.purchase_price,
            product.unit_weight,
            product.current_stock,
            product.minimum_stock,
            product.supplier
        ))

        conn.commit()

        row = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        print("PRODUCT ADDED SUCCESSFULLY")
        print("Product ID:", product_id)
        print("================================\n")

        conn.close()

        return dict(row)

    except Exception as e:

        conn.rollback()

        print("\n========== ADD PRODUCT ERROR ==========")
        print("ERROR TYPE:", type(e).__name__)
        print("ERROR:", str(e))
        print("=======================================\n")

        conn.close()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================
# UPDATE PRODUCT
# PUT /products/{product_id}
# =========================

@app.put("/products/{product_id}")
def update_product(product_id: str, product: ProductCreate):

    conn = get_connection()

    cursor = conn.execute("""
        UPDATE products
        SET
            name = ?,
            category = ?,
            rfid_tag = ?,
            price = ?,
            purchase_price = ?,
            unit_weight = ?,
            current_stock = ?,
            minimum_stock = ?,
            supplier = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        product.name,
        product.category,
        product.rfid_tag,
        product.price,
        product.purchase_price,
        product.unit_weight,
        product.current_stock,
        product.minimum_stock,
        product.supplier,
        product_id
    ))

    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    row = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    conn.close()

    return dict(row)


# =========================
# DELETE PRODUCT
# DELETE /products/{product_id}
# =========================

@app.delete("/products/{product_id}")
def delete_product(product_id: str):

    conn = get_connection()

    cursor = conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    conn.close()

    return {
        "status": "success",
        "message": "Product deleted successfully"
    }


# =========================
# GET ALL TROLLEYS
# =========================

@app.get("/trolleys")
def get_trolleys():

    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM trolleys
        ORDER BY trolley_number
    """).fetchall()

    conn.close()

    trolleys = [
        dict(row)
        for row in rows
    ]

    return {
        "count": len(trolleys),
        "trolleys": trolleys
    }


# =========================
# TROLLEY DATA MODEL
# =========================

class TrolleyCreate(BaseModel):
    trolley_number: str
    status: str
    firmware_version: str


# =========================
# CREATE TROLLEY
# POST /trolleys
# =========================

@app.post("/trolleys")
def create_trolley(trolley: TrolleyCreate):

    conn = get_connection()
    trolley_id = str(uuid.uuid4())

    cursor = conn.execute("""
        INSERT INTO trolleys (
            id,
            trolley_number,
            status,
            firmware_version
        )
        VALUES (?, ?, ?, ?)
    """, (
        trolley_id,
        trolley.trolley_number,
        trolley.status,
        trolley.firmware_version
    ))

    conn.commit()

    row = conn.execute(
        "SELECT * FROM trolleys WHERE id = ?",
        (trolley_id,)
    ).fetchone()

    conn.close()

    return dict(row)
# =========================
# CART ITEM DATA MODEL
# =========================

class CartItemCreate(BaseModel):
    trolley_id: str
    product_id: str
    quantity: int
    expected_weight: float
    actual_weight: float
    verified: bool

class VerifyCartItem(BaseModel):
    trolley_id: str
    product_id: str
    actual_weight: float
    quantity: int = 1

class UpdateAlertStatus(BaseModel):
    status: str

class CheckoutRequest(BaseModel):
    trolley_id: str
    payment_status: str  

class StockOrderCreate(BaseModel):
    supplier: str
    expected_date: str | None = None


class StockOrderItemCreate(BaseModel):
    order_id: str
    product_id: str
    quantity_ordered: int
    purchase_price: float     

class ReceiveStockRequest(BaseModel):
    order_item_id: str
    quantity_received: int
# =========================
# STOCK ORDERS
# =========================



@app.post("/stock-orders")
def create_stock_order(order: StockOrderCreate):

    conn = get_connection()

    try:
        # Generate UUID for stock order
        order_id = str(uuid.uuid4())

        cursor = conn.execute("""
            INSERT INTO stock_orders (
                id,
                supplier,
                expected_date,
                status
            )
            VALUES (?, ?, ?, ?)
        """, (
            order_id,
            order.supplier,
            order.expected_date,
            "pending"
        ))

        conn.commit()

        row = conn.execute("""
            SELECT *
            FROM stock_orders
            WHERE id = ?
        """, (order_id,)).fetchone()

        if not row:
            return {
                "status": "error",
                "message": "Stock order could not be created"
            }

        return {
            "status": "created",
            "message": "Stock order created successfully",
            "order": dict(row)
        }

    except Exception as e:
        conn.rollback()

        print("Create stock order error:", e)

        return {
            "status": "error",
            "message": "Stock order could not be created"
        }

    finally:
        conn.close()




# =========================================================
# AI EVENTS
# POST /ai/events
# =========================================================

@app.post("/ai/events")
def ingest_ai_event(event: AIEvent):
    conn = get_connection()

    try:
        event_id = str(uuid.uuid4())

        conn.execute("""
            INSERT INTO ai_events (
                id,
                event_type,
                session_id,
                trolley_id,
                zone_id,
                value,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            event.event_type,
            event.session_id,
            event.trolley_id,
            event.zone_id,
            event.value,
            json.dumps(event.metadata or {})
        ))

        conn.commit()

        return {
            "status": "recorded",
            "event_id": event_id,
            "offline": True
        }

    finally:
        conn.close()


# =========================================================
# AI CONTROL ROOM
# GET /ai/control-room
# =========================================================

@app.get("/ai/control-room")
def ai_control_room():
    conn = get_connection()

    try:
        return control_room(conn)

    finally:
        conn.close()


# =========================================================
# AI INVENTORY
# GET /ai/inventory
# =========================================================

@app.get("/ai/inventory")
def ai_inventory():
    conn = get_connection()

    try:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "products": inventory_intelligence(
                conn,
                lookback_days=30,
                forecast_days=7
            )
        }

    finally:
        conn.close()


# =========================================================
# AI REVENUE LEAK RADAR
# GET /ai/revenue-leaks
# =========================================================

@app.get("/ai/revenue-leaks")
def ai_revenue_leaks():
    conn = get_connection()

    try:
        return revenue_leak_radar(conn)

    finally:
        conn.close()


# =========================================================
# AI SHOPPER
# GET /ai/shopper
# =========================================================

@app.get("/ai/shopper")
def ai_shopper():
    conn = get_connection()

    try:
        return shopper_intelligence(
            conn,
            lookback_days=30
        )

    finally:
        conn.close()


# =========================================================
# AI QUEUE
# GET /ai/queue
# =========================================================

@app.get("/ai/queue")
def ai_queue():
    conn = get_connection()

    try:
        return queue_intelligence(
            conn,
            horizon_minutes=15
        )

    finally:
        conn.close()


# =========================================================
# AI ASK
# GET /ai/ask?q=...
# =========================================================

@app.get("/ai/ask")
def ai_ask(q: str):
    question = (q or "").strip().lower()

    conn = get_connection()

    try:
        if any(k in question for k in [
            "stock",
            "inventory",
            "reorder",
            "stockout",
            "out of stock"
        ]):
            inv = inventory_intelligence(conn)

            risky = [
                p for p in inv
                if p["risk"] in (
                    "critical",
                    "high",
                    "medium"
                )
            ]

            if risky:
                p = risky[0]

                return {
                    "answer": (
                        f"{p['name']} is {p['risk']} risk. "
                        f"Current stock is {p['current_stock']} units, "
                        f"7-day demand forecast is "
                        f"{p['forecast_7d']:.1f}, and AI recommends "
                        f"ordering {p['recommended_order_qty']} units."
                    ),
                    "source": "local inventory intelligence"
                }

            return {
                "answer": (
                    "No product is currently above the configured "
                    "AI inventory risk thresholds."
                ),
                "source": "local inventory intelligence"
            }

        if any(k in question for k in [
            "queue",
            "wait",
            "counter",
            "checkout"
        ]):
            qdata = queue_intelligence(conn)

            return {
                "answer": (
                    f"Queue congestion risk is "
                    f"{qdata['congestion_risk']}. "
                    f"Active checkout carts: "
                    f"{qdata['active_checkout_carts']}. "
                    f"Predicted 15-minute load: "
                    f"{qdata['predicted_load_in_15min']}."
                ),
                "source": "local queue intelligence"
            }

        if any(k in question for k in [
            "shopper",
            "basket",
            "customer",
            "selling",
            "buy together"
        ]):
            s = shopper_intelligence(conn)

            pair = (
                s["top_product_pairs"][0]
                if s["top_product_pairs"]
                else None
            )

            extra = (
                f" Top observed product pair: "
                f"{pair['products'][0]} + {pair['products'][1]}."
                if pair else ""
            )

            return {
                "answer": (
                    f"Average basket value is "
                    f"₹{s['avg_basket_value']:.0f} "
                    f"with {s['avg_items_per_basket']:.1f} "
                    f"items per basket."
                    + extra
                ),
                "source": "local shopper intelligence"
            }

        if any(k in question for k in [
            "loss",
            "leak",
            "shrink",
            "anomaly",
            "guardian"
        ]):
            r = revenue_leak_radar(conn)

            return {
                "answer": (
                    f"Estimated revenue exposure from current "
                    f"inventory risks and active guardian events "
                    f"is ₹{r['estimated_exposure']:.0f}. "
                    f"There are {r['active_guardian_alerts']} "
                    f"active guardian alerts."
                ),
                "source": "local revenue-leak radar"
            }

        summary = control_room(conn)
        k = summary["kpis"]

        return {
            "answer": (
                f"Store snapshot: {k['high_risk_products']} "
                f"high-risk products, {k['low_stock_products']} "
                f"low-stock products, {k['active_guardian_alerts']} "
                f"active guardian alerts, queue risk "
                f"{k['queue_risk']}, and estimated revenue exposure "
                f"₹{k['revenue_exposure']:.0f}."
            ),
            "source": "local retail brain"
        }

    finally:
        conn.close()


# =========================================================
# AI WHAT-IF INVENTORY
# GET /ai/what-if/inventory
# =========================================================

@app.get("/ai/what-if/inventory")
def ai_what_if_inventory(product_id: str, extra_stock: int = 0):
    conn = get_connection()

    try:
        products = inventory_intelligence(conn)

        target = next(
            (
                p for p in products
                if str(p["id"]) == str(product_id)
            ),
            None
        )

        if not target:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        simulated_stock = (
            target["current_stock"] +
            max(0, int(extra_stock))
        )

        velocity = target["daily_sales_velocity"]

        simulated_days = (
            simulated_stock / velocity
            if velocity > 0
            else None
        )

        return {
            "product_id": product_id,
            "current_stock": target["current_stock"],
            "simulated_stock": simulated_stock,
            "current_days_to_stockout": target["days_to_stockout"],
            "simulated_days_to_stockout": (
                round(simulated_days, 1)
                if simulated_days is not None
                else None
            ),
            "recommended_order_now": target[
                "recommended_order_qty"
            ]
        }

    finally:
        conn.close()


# =========================================================
# AI WHAT-IF QUEUE
# GET /ai/what-if/queue
# =========================================================

@app.get("/ai/what-if/queue")
def ai_what_if_queue(additional_counters: int = 1):
    conn = get_connection()

    try:
        q = queue_intelligence(conn)

        if not q["data_ready"]:
            return {
                "data_ready": False,
                "message": q["data_note"]
            }

        counters = max(
            1,
            1 + int(additional_counters)
        )

        projected = q["predicted_load_in_15min"]
        per_counter = round(
            projected / counters,
            1
        )

        return {
            "data_ready": True,
            "additional_counters": max(
                0,
                int(additional_counters)
            ),
            "predicted_load": projected,
            "load_per_counter": per_counter,
            "recommendation": (
                "Open additional checkout capacity"
                if per_counter > 4
                else "Current capacity appears sufficient"
            )
        }

    finally:
        conn.close()


# =========================
# CHECKOUT
# POST /checkout
# =========================

@app.post("/checkout")
def checkout(request: CheckoutRequest):

    conn = get_connection()

    try:

        # =====================================================
        # 0. CHECK TROLLEY
        # =====================================================

        trolley = conn.execute("""
            SELECT *
            FROM trolleys
            WHERE id = ?
        """, (request.trolley_id,)).fetchone()

        if not trolley:
            return {
                "status": "not_found",
                "message": "Trolley not found"
            }

        # =====================================================
        # 1. PAYMENT MUST BE SUCCESSFUL
        # =====================================================

        if request.payment_status != "paid":
            return {
                "status": "payment_required",
                "message": "Checkout allowed only after successful payment"
            }

        # =====================================================
        # 2. GET CART
        # =====================================================

        cart_rows = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE trolley_id = ?
        """, (request.trolley_id,)).fetchall()

        cart_items = [
            dict(row)
            for row in cart_rows
        ]

        if not cart_items:
            return {
                "status": "empty_cart",
                "message": "No items found in trolley"
            }

        # =====================================================
        # 3. ALL ITEMS MUST BE VERIFIED
        # =====================================================

        unverified_items = [
            item
            for item in cart_items
            if not item["verified"]
        ]

        if unverified_items:
            return {
                "status": "verification_required",
                "message": "All cart items must be verified before checkout"
            }

        # =====================================================
        # 4. CALCULATE TOTAL + PREPARE ITEMS
        # =====================================================

        total_amount = 0
        transaction_items = []

        for item in cart_items:

            product = conn.execute("""
                SELECT *
                FROM products
                WHERE id = ?
            """, (item["product_id"],)).fetchone()

            if not product:
                return {
                    "status": "product_not_found",
                    "message": f"Product not found: {item['product_id']}"
                }

            product = dict(product)

            quantity = int(item["quantity"])
            unit_price = float(product["price"])
            item_total = unit_price * quantity

            # Check stock
            current_stock = int(product["current_stock"])

            if current_stock < quantity:
                return {
                    "status": "insufficient_stock",
                    "message": (
                        f"Insufficient stock for {product['name']}. "
                        f"Available: {current_stock}, "
                        f"Required: {quantity}"
                    )
                }

            total_amount += item_total

            transaction_items.append({
                "product_id": product["id"],
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": item_total
            })

        # =====================================================
        # 5. GENERATE TRANSACTION UUID
        # =====================================================

        transaction_id = str(uuid.uuid4())

        # =====================================================
        # 6. CREATE TRANSACTION
        # =====================================================

        conn.execute("""
            INSERT INTO transactions (
                id,
                trolley_id,
                total_amount,
                payment_status
            )
            VALUES (?, ?, ?, ?)
        """, (
            transaction_id,
            request.trolley_id,
            total_amount,
            "paid"
        ))

        # =====================================================
        # 7. ADD TRANSACTION ITEMS
        # =====================================================

        for item in transaction_items:

            transaction_item_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO transaction_items (
                    id,
                    transaction_id,
                    product_id,
                    quantity,
                    unit_price,
                    total_price
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transaction_item_id,
                transaction_id,
                item["product_id"],
                item["quantity"],
                item["unit_price"],
                item["total_price"]
            ))

        # =====================================================
        # 8. DEDUCT INVENTORY + CREATE SALE MOVEMENT
        # =====================================================

        for item in transaction_items:

            product = conn.execute("""
                SELECT current_stock
                FROM products
                WHERE id = ?
            """, (item["product_id"],)).fetchone()

            if not product:
                raise Exception(
                    f"Product not found during stock update: "
                    f"{item['product_id']}"
                )

            current_stock = int(product["current_stock"])

            new_stock = current_stock - item["quantity"]

            conn.execute("""
                UPDATE products
                SET
                    current_stock = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                new_stock,
                item["product_id"]
            ))

            # Generate inventory movement UUID
            movement_id = str(uuid.uuid4())

            # Record SALE movement
            conn.execute("""
                INSERT INTO inventory_movements (
                    id,
                    product_id,
                    type,
                    quantity,
                    reference_id
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                movement_id,
                item["product_id"],
                "SALE",
                item["quantity"],
                transaction_id
            ))

        # =====================================================
        # 9. CLEAR CART
        # =====================================================

        conn.execute("""
            DELETE FROM cart_items
            WHERE trolley_id = ?
        """, (request.trolley_id,))

        # =====================================================
        # 10. MAKE TROLLEY AVAILABLE
        # =====================================================

        conn.execute("""
            UPDATE trolleys
            SET
                status = 'available',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (request.trolley_id,))

        # =====================================================
        # 11. COMMIT EVERYTHING
        # =====================================================

        conn.commit()

        return {
            "status": "success",
            "message": "Checkout completed successfully",
            "transaction_id": transaction_id,
            "total_amount": total_amount,
            "items_count": len(cart_items),
            "trolley_status": "available"
        }

    except Exception as e:

        conn.rollback()

        print("Checkout error:", e)

        return {
            "status": "error",
            "message": "Checkout could not be completed"
        }

    finally:

        conn.close()

# =========================
# UPDATE ALERT STATUS
# PUT /alerts/{alert_id}
# =========================

@app.put("/alerts/{alert_id}")
def update_alert_status(alert_id: str, alert: UpdateAlertStatus):

    # Only these statuses are allowed
    if alert.status not in ["active", "resolved", "dismissed"]:
        return {
            "status": "invalid",
            "message": "Status must be active, resolved, or dismissed"
        }

    conn = get_connection()

    try:

        # Check alert exists
        existing_alert = conn.execute("""
            SELECT *
            FROM alerts
            WHERE id = ?
        """, (alert_id,)).fetchone()

        if not existing_alert:
            return {
                "status": "not_found",
                "message": "Alert not found"
            }

        # Set resolved time when resolved/dismissed
        resolved_at = None

        if alert.status in ["resolved", "dismissed"]:
            from datetime import datetime, timezone
            resolved_at = datetime.now(timezone.utc).isoformat()

        # Update alert
        conn.execute("""
            UPDATE alerts
            SET
                status = ?,
                resolved_at = ?
            WHERE id = ?
        """, (
            alert.status,
            resolved_at,
            alert_id
        ))

        conn.commit()

        # Get updated alert
        updated_alert = conn.execute("""
            SELECT *
            FROM alerts
            WHERE id = ?
        """, (alert_id,)).fetchone()

        return {
            "status": "updated",
            "alert": dict(updated_alert)
        }

    except Exception as e:

        conn.rollback()

        print("Alert update error:", e)

        return {
            "status": "error",
            "message": "Alert could not be updated"
        }

    finally:
        conn.close()
# =========================
# LOCAL DATA API ROUTES
# =========================

@app.get("/transactions")
def get_transactions():
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, tr.trolley_number,
               COUNT(ti.id) AS items
        FROM transactions t
        LEFT JOIN trolleys tr ON tr.id = t.trolley_id
        LEFT JOIN transaction_items ti ON ti.transaction_id = t.id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/inventory-movements")
def get_inventory_movements(type: str | None = None):
    conn = get_connection()
    if type:
        rows = conn.execute("""
            SELECT im.*, p.name AS product_name
            FROM inventory_movements im
            LEFT JOIN products p ON p.id = im.product_id
            WHERE im.type = ?
            ORDER BY im.created_at DESC
        """, (type,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT im.*, p.name AS product_name
            FROM inventory_movements im
            LEFT JOIN products p ON p.id = im.product_id
            ORDER BY im.created_at DESC
        """).fetchall()
    conn.close()
    result=[]
    for r in rows:
        d=dict(r)
        d["products"]={"name":d.pop("product_name",None)}
        result.append(d)
    return result

@app.get("/alerts")
def get_alerts(include_resolved: bool = True):
    conn=get_connection()
    query="""
        SELECT a.*, tr.trolley_number, p.name AS product_name
        FROM alerts a
        LEFT JOIN trolleys tr ON tr.id=a.trolley_id
        LEFT JOIN products p ON p.id=a.product_id
    """
    params=()
    if not include_resolved:
        query += " WHERE a.status != 'resolved' "
    query += " ORDER BY a.created_at DESC"
    rows=conn.execute(query,params).fetchall()
    conn.close()
    result=[]
    for r in rows:
        d=dict(r)
        d["trolleys"]={"trolley_number":d.pop("trolley_number",None)}
        d["products"]={"name":d.pop("product_name",None)}
        result.append(d)
    return result

@app.put("/trolleys/{trolley_id}")
def update_trolley(trolley_id: str, payload: dict):
    status=payload.get("status")
    allowed=["available","shopping","alert","checkout","offline"]
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid trolley status")
    conn=get_connection()
    cur=conn.execute("""
        UPDATE trolleys SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
    """,(status,trolley_id))
    conn.commit()
    row=conn.execute("SELECT * FROM trolleys WHERE id=?",(trolley_id,)).fetchone()
    conn.close()
    if cur.rowcount==0 or not row:
        raise HTTPException(status_code=404, detail="Trolley not found")
    return dict(row)

@app.get("/stock-orders")
def get_stock_orders():
    conn=get_connection()
    rows=conn.execute("""
        SELECT so.*, soi.id AS item_id, soi.product_id, soi.quantity_ordered,
               soi.quantity_received, soi.purchase_price, p.name AS product_name
        FROM stock_orders so
        LEFT JOIN stock_order_items soi ON soi.order_id=so.id
        LEFT JOIN products p ON p.id=soi.product_id
        ORDER BY so.order_date DESC
    """).fetchall()
    conn.close()
    result=[]
    for r in rows:
        d=dict(r)
        item={
            "id":d.pop("item_id",None),
            "product_id":d.pop("product_id",None),
            "quantity_ordered":d.pop("quantity_ordered",0) or 0,
            "quantity_received":d.pop("quantity_received",0) or 0,
            "purchase_price":d.pop("purchase_price",0) or 0,
            "products":{"name":d.pop("product_name",None)}
        }
        d["stock_order_items"]=[] if item["id"] is None else [item]
        result.append(d)
    return result

@app.post("/stock-order-items")
def create_stock_order_item(item: StockOrderItemCreate):
    conn=get_connection()
    item_id=str(uuid.uuid4())
    try:
        conn.execute("""
            INSERT INTO stock_order_items
            (id, order_id, product_id, quantity_ordered, quantity_received, purchase_price)
            VALUES (?, ?, ?, ?, 0, ?)
        """,(item_id,item.order_id,item.product_id,item.quantity_ordered,item.purchase_price))
        conn.commit()
        row=conn.execute("SELECT * FROM stock_order_items WHERE id=?",(item_id,)).fetchone()
        return dict(row)
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=400,detail=str(e))
    finally: conn.close()

@app.post("/receive-stock")
def receive_stock(request: ReceiveStockRequest):
    conn=get_connection()
    try:
        item=conn.execute("SELECT * FROM stock_order_items WHERE id=?",(request.order_item_id,)).fetchone()
        if not item: raise HTTPException(status_code=404,detail="Order item not found")
        item=dict(item)
        remaining=int(item["quantity_ordered"])-int(item["quantity_received"] or 0)
        qty=int(request.quantity_received)
        if qty<=0 or qty>remaining: raise HTTPException(status_code=400,detail=f"Only {remaining} units are remaining")
        new_received=int(item["quantity_received"] or 0)+qty
        new_status="received" if new_received>=int(item["quantity_ordered"]) else "partially_received"
        conn.execute("UPDATE stock_order_items SET quantity_received=? WHERE id=?",(new_received,item["id"]))
        conn.execute("UPDATE stock_orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",(new_status,item["order_id"]))
        conn.execute("UPDATE products SET current_stock=current_stock+?, updated_at=CURRENT_TIMESTAMP WHERE id=?",(qty,item["product_id"]))
        conn.execute("""INSERT INTO inventory_movements (id,product_id,type,quantity,reference_id) VALUES (?,?,?,?,?)""",(str(uuid.uuid4()),item["product_id"],"PURCHASE",qty,item["order_id"]))
        conn.commit()
        order=conn.execute("SELECT * FROM stock_orders WHERE id=?",(item["order_id"],)).fetchone()
        return {"status":"success","order":dict(order),"item":dict(conn.execute("SELECT * FROM stock_order_items WHERE id=?",(item["id"],)).fetchone())}
    except HTTPException: conn.rollback(); raise
    except Exception as e: conn.rollback(); print("Receive stock error:",e); raise HTTPException(status_code=500,detail="Receive stock failed")
    finally: conn.close()

# =========================
# VERIFY CART ITEM
# POST /verify-cart-item
# =========================

@app.post("/verify-cart-item")
def verify_cart_item(item: VerifyCartItem):

    conn = get_connection()

    try:

        # =====================================================
        # 0. CHECK TROLLEY
        # =====================================================

        trolley = conn.execute("""
            SELECT *
            FROM trolleys
            WHERE id = ?
        """, (item.trolley_id,)).fetchone()

        if not trolley:
            return {
                "status": "not_found",
                "message": "Trolley not found"
            }

        # =====================================================
        # 1. GET PRODUCT
        # =====================================================

        product = conn.execute("""
            SELECT *
            FROM products
            WHERE id = ?
        """, (item.product_id,)).fetchone()

        if not product:
            return {
                "status": "not_found",
                "message": "Product not found"
            }

        product = dict(product)

        # =====================================================
        # 2. VALIDATE UNIT WEIGHT
        # =====================================================

        if (
            product["unit_weight"] is None
            or float(product["unit_weight"]) <= 0
        ):
            return {
                "status": "invalid",
                "message": "Product unit weight must be greater than 0"
            }

        # =====================================================
        # 3. CALCULATE EXPECTED WEIGHT
        # =====================================================

        unit_weight = float(product["unit_weight"])

        expected_weight = (
            unit_weight * item.quantity
        )

        # =====================================================
        # 4. CALCULATE DIFFERENCE
        # =====================================================

        difference_percent = (
            abs(item.actual_weight - expected_weight)
            / expected_weight
        ) * 100

        # =====================================================
        # 5. 5% TOLERANCE
        # =====================================================

        verified = difference_percent <= 5

        # =====================================================
        # 6. VERIFIED → ADD TO CART
        # =====================================================

        if verified:

            cursor = conn.execute("""
                INSERT INTO cart_items (
                    trolley_id,
                    product_id,
                    quantity,
                    expected_weight,
                    actual_weight,
                    verified
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item.trolley_id,
                item.product_id,
                item.quantity,
                expected_weight,
                item.actual_weight,
                True
            ))

            conn.commit()

            cart_item = conn.execute("""
                SELECT *
                FROM cart_items
                WHERE rowid = ?
            """, (cursor.lastrowid,)).fetchone()

            return {
                "status": "verified",
                "verified": True,
                "expected_weight": expected_weight,
                "actual_weight": item.actual_weight,
                "difference_percent": round(
                    difference_percent,
                    2
                ),
                "product": product,
                "cart_item": dict(cart_item)
            }

        # =====================================================
        # 7. MISMATCH → CREATE ALERT
        # =====================================================

        alert_cursor = conn.execute("""
            INSERT INTO alerts (
                trolley_id,
                product_id,
                type,
                expected_value,
                actual_value,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            item.trolley_id,
            item.product_id,
            "weight_mismatch",
            expected_weight,
            item.actual_weight,
            "active"
        ))

        conn.commit()

        alert = conn.execute("""
            SELECT *
            FROM alerts
            WHERE id = ?
        """, (alert_cursor.lastrowid,)).fetchone()

        return {
            "status": "mismatch",
            "verified": False,
            "expected_weight": expected_weight,
            "actual_weight": item.actual_weight,
            "difference_percent": round(
                difference_percent,
                2
            ),
            "message": "Weight mismatch. Verification required.",
            "alert": dict(alert) if alert else None
        }

    except Exception as e:

        conn.rollback()

        print("Verify cart item error:", e)

        return {
            "status": "error",
            "message": "Cart item verification failed"
        }

    finally:
        conn.close()
# =========================
# GET CART ITEMS
# GET /cart-items
# =========================
@app.get("/cart-items")
def get_cart_items():

    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                ci.id,
                ci.trolley_id,
                ci.product_id,
                ci.quantity,
                ci.expected_weight,
                ci.actual_weight,
                ci.verified,

                p.name AS product_name,
                p.price AS product_price

            FROM cart_items ci

            LEFT JOIN products p
                ON p.id = ci.product_id

            ORDER BY ci.rowid DESC
        """).fetchall()

        cart_items = []

        for row in rows:

            item = dict(row)

            item["products"] = {
                "id": item["product_id"],
                "name": item["product_name"],
                "price": item["product_price"]
            }

            del item["product_name"]
            del item["product_price"]

            cart_items.append(item)

        return cart_items

    except Exception as e:

        print("Get cart items error:", e)

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch cart items"
        )

    finally:
        conn.close()
# =========================
# ADD ITEM TO CART
# POST /cart-items
# =========================

@app.post("/cart-items")
def add_cart_item(item: CartItemCreate):

    conn = get_connection()

    try:

        # Check trolley exists
        trolley = conn.execute("""
            SELECT id
            FROM trolleys
            WHERE id = ?
        """, (item.trolley_id,)).fetchone()

        if not trolley:
            return {
                "status": "not_found",
                "message": "Trolley not found"
            }

        # Check product exists
        product = conn.execute("""
            SELECT id
            FROM products
            WHERE id = ?
        """, (item.product_id,)).fetchone()

        if not product:
            return {
                "status": "not_found",
                "message": "Product not found"
            }

        # Generate unique cart item ID
        cart_item_id = str(uuid.uuid4())

        # Add cart item
        conn.execute("""
            INSERT INTO cart_items (
                id,
                trolley_id,
                product_id,
                quantity,
                expected_weight,
                actual_weight,
                verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cart_item_id,
            item.trolley_id,
            item.product_id,
            item.quantity,
            item.expected_weight,
            item.actual_weight,
            item.verified
        ))

        conn.commit()

        # Get newly created cart item
        cart_item = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE id = ?
        """, (cart_item_id,)).fetchone()

        return {
            "status": "added",
            "cart_item": dict(cart_item)
        }

    except Exception as e:

        conn.rollback()

        print("Add cart item error:", e)

        return {
            "status": "error",
            "message": "Cart item could not be added"
        }

    finally:
        conn.close()

from fastapi import FastAPI, HTTPException, Body
from database import get_connection
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json
import paho.mqtt.client as mqtt
import uuid
import razorpay


# =========================
# LOAD ENVIRONMENT
# =========================

load_dotenv()
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)







# =========================
# MQTT CONFIGURATION
# =========================

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "cart/+/scan"


def on_connect(client, userdata, flags, reason_code, properties):

    print("MQTT connected successfully")

    # Subscribe to RFID scan messages
    client.subscribe("cart/+/scan")
    print("Subscribed to: cart/+/scan")

    # Subscribe to weight messages
    client.subscribe("cart/+/weight")
    print("Subscribed to: cart/+/weight")

    # Subscribe to cart status messages
    client.subscribe("cart/+/status")
    print("Subscribed to: cart/+/status")

def on_message(client, userdata, msg):
    try:
        # Get raw MQTT message
        raw_message = msg.payload.decode()

        print("\n========== MQTT MESSAGE ==========")
        print("Topic:", msg.topic)
        print("Raw Message:", raw_message)

        # Convert JSON to Python dictionary
        payload = json.loads(raw_message)

        print("Payload:", payload)

        # Get cart number
        topic_parts = msg.topic.split("/")

        if len(topic_parts) < 3:
            print("Invalid MQTT topic:", msg.topic)
            return

        cart_id = topic_parts[1]
        message_type = topic_parts[2]

        # =========================================================
        # CART STATUS SYNCHRONIZATION
        # Topic: cart/05/status
        # =========================================================

        if message_type == "status":

            status = payload.get("status")

            if not status:
                print("Cart status missing in message")
                return

            print("CART STATUS UPDATE")
            print("Cart:", cart_id)
            print("Status:", status)

            # -----------------------------------------------------
            # Allowed trolley statuses
            # -----------------------------------------------------

            allowed_statuses = [
                "available",
                "shopping",
                "alert",
                "checkout",
                "offline"
            ]

            if status not in allowed_statuses:
                print("Invalid cart status:", status)
                return

            # -----------------------------------------------------
            # Update trolley status in database
            # -----------------------------------------------------

            conn = get_connection()

            cursor = conn.execute("""
                UPDATE trolleys
                SET
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE trolley_number = ?
            """, (
                status,
                f"Cart {cart_id}"
            ))

            conn.commit()

            trolley_updated = cursor.rowcount > 0

            conn.close()

            if not trolley_updated:
                print("Trolley not found:", cart_id)
                return

            print("Cart status updated successfully")
            print("Cart:", cart_id)
            print("New Status:", status)

            # -----------------------------------------------------
            # Send confirmation through MQTT
            # -----------------------------------------------------

            status_response = {
                "cart_id": cart_id,
                "status": status,
                "message": "Cart status synchronized"
            }

            mqtt_client.publish(
                f"cart/{cart_id}/status_response",
                json.dumps(status_response)
            )

            print("Status confirmation sent")
            print("==================================\n")

            return

        # =========================================================
        # WEIGHT VERIFICATION
        # Topic: cart/05/weight
        # =========================================================

        if message_type == "weight":

            product_id = payload.get("product_id")
            actual_weight = payload.get("actual_weight")
            quantity = payload.get("quantity", 1)

            if not product_id:
                print("Product ID missing in weight message")
                return

            if actual_weight is None:
                print("Actual weight missing in message")
                return

            print("WEIGHT VERIFICATION REQUEST")
            print("Cart:", cart_id)
            print("Product ID:", product_id)
            print("Quantity:", quantity)
            print("Actual Weight:", actual_weight)

            # -----------------------------------------------------
            # Find trolley
            # -----------------------------------------------------

            conn = get_connection()

            trolley = conn.execute("""
                SELECT id
                FROM trolleys
                WHERE trolley_number = ?
            """, (
                f"Cart {cart_id}",
            )).fetchone()

            if not trolley:
                conn.close()

                print("Trolley not found:", cart_id)

                verification_response = {
                    "status": "not_found",
                    "verified": False,
                    "message": "Trolley not found"
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                return

            trolley_id = trolley["id"]

            # -----------------------------------------------------
            # Find product
            # -----------------------------------------------------

            product_row = conn.execute("""
                SELECT *
                FROM products
                WHERE id = ?
            """, (
                product_id,
            )).fetchone()

            if not product_row:
                conn.close()

                print("Product not found:", product_id)

                verification_response = {
                    "status": "not_found",
                    "verified": False,
                    "message": "Product not found"
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                return

            product = dict(product_row)

            # -----------------------------------------------------
            # Validate unit weight
            # -----------------------------------------------------

            if (
                product["unit_weight"] is None
                or float(product["unit_weight"]) <= 0
            ):
                conn.close()

                print("Invalid product unit weight")

                verification_response = {
                    "status": "invalid",
                    "verified": False,
                    "message": "Product unit weight must be greater than 0"
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                return

            # -----------------------------------------------------
            # Calculate expected weight
            # -----------------------------------------------------

            unit_weight = float(product["unit_weight"])
            expected_weight = unit_weight * int(quantity)

            actual_weight = float(actual_weight)

            # -----------------------------------------------------
            # Calculate difference
            # -----------------------------------------------------

            difference_percent = (
                abs(actual_weight - expected_weight)
                / expected_weight
            ) * 100

            # 5% tolerance
            verified = difference_percent <= 5

            print("Expected Weight:", expected_weight)
            print("Actual Weight:", actual_weight)
            print(
                "Difference:",
                round(difference_percent, 2),
                "%"
            )

            # =====================================================
            # VERIFIED
            # =====================================================

            if verified:

                conn.execute("""
                    INSERT INTO cart_items (
                        trolley_id,
                        product_id,
                        quantity,
                        expected_weight,
                        actual_weight,
                        verified
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    trolley_id,
                    product_id,
                    int(quantity),
                    expected_weight,
                    actual_weight,
                    True
                ))

                conn.commit()
                conn.close()

                verification_response = {
                    "status": "verified",
                    "verified": True,
                    "product_id": product_id,
                    "product_name": product["name"],
                    "price": product["price"],
                    "expected_weight": expected_weight,
                    "actual_weight": actual_weight,
                    "difference_percent": round(
                        difference_percent,
                        2
                    )
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                print("WEIGHT VERIFIED")
                print("Verification response sent")

            # =====================================================
            # MISMATCH
            # =====================================================

            else:

                # -------------------------------------------------
                # Create alert in database
                # -------------------------------------------------

                conn.execute("""
                    INSERT INTO alerts (
                        trolley_id,
                        product_id,
                        type,
                        expected_value,
                        actual_value,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    trolley_id,
                    product_id,
                    "weight_mismatch",
                    expected_weight,
                    actual_weight,
                    "active"
                ))

                conn.commit()
                conn.close()

                # -------------------------------------------------
                # Send alert through MQTT
                # -------------------------------------------------

                alert_message = {
                    "type": "weight_mismatch",
                    "product_id": product_id,
                    "expected_weight": expected_weight,
                    "actual_weight": actual_weight,
                    "difference_percent": round(
                        difference_percent,
                        2
                    ),
                    "message": "Weight mismatch. Verification required.",
                    "status": "active"
                }

                alert_topic = f"cart/{cart_id}/alert"

                mqtt_client.publish(
                    alert_topic,
                    json.dumps(alert_message)
                )

                print("MQTT alert sent")
                print("Alert Topic:", alert_topic)
                print("Alert:", alert_message)

                # -------------------------------------------------
                # Send verification response
                # -------------------------------------------------

                verification_response = {
                    "status": "mismatch",
                    "verified": False,
                    "product_id": product_id,
                    "product_name": product["name"],
                    "expected_weight": expected_weight,
                    "actual_weight": actual_weight,
                    "difference_percent": round(
                        difference_percent,
                        2
                    ),
                    "message": "Weight mismatch. Verification required."
                }

                mqtt_client.publish(
                    f"cart/{cart_id}/verification",
                    json.dumps(verification_response)
                )

                print("WEIGHT MISMATCH")
                print("Alert created")
                print("Verification response sent")

            print("==================================\n")
            return

        # =========================================================
        # RFID SCAN
        # Topic: cart/01/scan
        # =========================================================

        if message_type == "scan":

            # Get RFID
            rfid = payload.get("rfid")

            if not rfid:
                print("RFID missing in message")
                return

            print("RFID SCAN")
            print("RFID:", rfid)
            print("Cart:", cart_id)

            # -----------------------------------------------------
            # Search product
            # -----------------------------------------------------

            conn = get_connection()

            product_row = conn.execute("""
                SELECT *
                FROM products
                WHERE rfid_tag = ?
            """, (
                rfid,
            )).fetchone()

            # -----------------------------------------------------
            # Product found
            # -----------------------------------------------------

            if product_row:

                product = dict(product_row)

                print("RFID MATCH FOUND")
                print("Product:", product["name"])
                print("Price:", product["price"])
                print("Weight:", product["unit_weight"])

                trolley = conn.execute("""
                    SELECT id
                    FROM trolleys
                    WHERE trolley_number = ?
                """, (f"Cart {cart_id}",)).fetchone()

                if not trolley:
                    print("Trolley not found:", cart_id)
                    conn.close()
                    return

                trolley_id = trolley["id"]

                existing_item = conn.execute("""
                    SELECT *
                    FROM cart_items
                    WHERE trolley_id = ? AND product_id = ?
                """, (trolley_id, product["id"])).fetchone()

                if existing_item:
                    new_quantity = int(existing_item["quantity"]) + 1
                    new_expected_weight = float(product["unit_weight"]) * new_quantity

                    # Handle old cart items that may have a NULL ID
                    cart_item_id = existing_item["id"]

                    if not cart_item_id:
                        cart_item_id = str(uuid.uuid4())

                        conn.execute("""
                            UPDATE cart_items
                            SET id = ?,
                                quantity = ?,
                                expected_weight = ?,
                                verified = 0
                            WHERE trolley_id = ?
                            AND product_id = ?
                        """, (
                            cart_item_id,
                            new_quantity,
                            new_expected_weight,
                            trolley_id,
                            product["id"]
                        ))

                        print("Old cart item had NULL ID")
                        print("New Cart Item ID:", cart_item_id)

                    else:
                        conn.execute("""
                            UPDATE cart_items
                            SET quantity = ?,
                                expected_weight = ?,
                                verified = 0
                            WHERE id = ?
                        """, (
                            new_quantity,
                            new_expected_weight,
                            cart_item_id
                        ))

                    print("Existing cart item updated")
                    print("New quantity:", new_quantity)

                else:
                    cart_item_id = str(uuid.uuid4())

                    conn.execute("""
                        INSERT INTO cart_items (
                            id, trolley_id, product_id, quantity,
                            expected_weight, actual_weight, verified
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cart_item_id, trolley_id, product["id"], 1,
                        float(product["unit_weight"]), 0, False
                    ))

                    print("New cart item created")
                    print("Cart Item ID:", cart_item_id)

                conn.commit()

                cart_item = conn.execute("""
                    SELECT * FROM cart_items WHERE id = ?
                """, (cart_item_id,)).fetchone()

                if not cart_item:
                    print("Cart item could not be found after update")
                    conn.close()
                    return

                product_response = {
                    "status": "added",
                    "rfid": rfid,
                    "product_id": product["id"],
                    "cart_item_id": cart_item["id"],
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": cart_item["quantity"],
                    "expected_weight": cart_item["expected_weight"],
                    "verified": False
                }

                response_topic = f"cart/{cart_id}/product"
                mqtt_client.publish(response_topic, json.dumps(product_response))

                print("Product added to cart")
                print("Response Topic:", response_topic)
                print("Response:", product_response)

                conn.close()

            # -----------------------------------------------------
            # Product not found
            # -----------------------------------------------------

            else:

                print("UNREGISTERED RFID DETECTED")
                print("RFID:", rfid)
                print("Cart:", cart_id)

                alert_message = {
                    "type": "unregistered_item",
                    "rfid": rfid,
                    "message": "Unregistered RFID detected",
                    "status": "active"
                }

                alert_topic = f"cart/{cart_id}/alert"

                mqtt_client.publish(
                    alert_topic,
                    json.dumps(alert_message)
                )

                print("Alert sent")
                print("Alert Topic:", alert_topic)

                # -------------------------------------------------
                # Find trolley
                # -------------------------------------------------

                trolley = conn.execute("""
                    SELECT id
                    FROM trolleys
                    WHERE trolley_number = ?
                """, (
                    f"Cart {cart_id}",
                )).fetchone()

                # -------------------------------------------------
                # Save alert
                # -------------------------------------------------

                if trolley:

                    trolley_id = trolley["id"]

                    conn.execute("""
                        INSERT INTO alerts (
                            trolley_id,
                            product_id,
                            type,
                            expected_value,
                            actual_value,
                            status
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        trolley_id,
                        None,
                        "unregistered_item",
                        None,
                        rfid,
                        "active"
                    ))

                    conn.commit()

                    print("Alert saved in database")

                else:
                    print("Trolley not found:", cart_id)

                conn.close()

            print("==================================\n")
            return

        # =========================================================
        # UNKNOWN MQTT MESSAGE TYPE
        # =========================================================

        print("Unknown MQTT message type:", message_type)

    except json.JSONDecodeError as e:

        print("INVALID JSON RECEIVED")
        print("Raw MQTT message:", msg.payload.decode())
        print("JSON error:", e)

    except Exception as e:

        print("MQTT message error:", e)

        

        
mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smart-retail-edge"
)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message        
@app.on_event("startup")
def start_mqtt():
    print("Starting MQTT connection...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()


@app.on_event("shutdown")
def stop_mqtt():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

# =========================
# BASIC ROUTES
# =========================

@app.get("/")
def root():
    return {
        "system": "Smart Retail Intelligence",
        "status": "Edge Server Online"
    }


# =====================================================
# SYSTEM COMPONENT STATUS
# =====================================================
@app.get("/health")
def health():
    return {"status": "healthy"}
@app.get("/system-status")
def system_status():

    # -------------------------------------------------
    # MQTT STATUS
    # -------------------------------------------------

    mqtt_connected = mqtt_client.is_connected()


    # -------------------------------------------------
    # DATABASE STATUS
    # -------------------------------------------------

    database_connected = False

    try:

        conn = get_connection()

        conn.execute("""
            SELECT 1
            FROM products
            LIMIT 1
        """).fetchone()

        conn.close()

        database_connected = True

    except Exception as e:

        print("SQLite database health check failed:", e)


    # -------------------------------------------------
    # FASTAPI STATUS
    # -------------------------------------------------

    fastapi_connected = True


    # -------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------

    return {

        "fastapi": (
            "connected"
            if fastapi_connected
            else "offline"
        ),

        "mqtt": (
            "connected"
            if mqtt_connected
            else "offline"
        ),

        "database": (
            "connected"
            if database_connected
            else "offline"
        )

    } 

# =========================
# PRODUCT DATA MODEL
# =========================

class ProductCreate(BaseModel):
    name: str
    category: str
    rfid_tag: str | None = None
    price: float
    purchase_price: float
    unit_weight: float
    current_stock: int
    minimum_stock: int
    supplier: str
@app.get("/products")
def get_products():
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM products
        ORDER BY name
    """).fetchall()

    conn.close()

    products = [dict(row) for row in rows]

    return {
        "count": len(products),
        "products": products
    }
# =========================
# GET ALL PRODUCTS
# ========================
class PaymentCreate(BaseModel):
    trolley_id: str

@app.post("/products")
def create_product(product: ProductCreate = Body(...)):

    conn = get_connection()

    try:
        product_id = str(uuid.uuid4())

        print("\n========== ADD PRODUCT ==========")
        print("Product received:", product.model_dump())

        cursor = conn.execute("""
            INSERT INTO products (
                id,
                name,
                category,
                rfid_tag,
                price,
                purchase_price,
                unit_weight,
                current_stock,
                minimum_stock,
                supplier
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            product.name,
            product.category,
            product.rfid_tag,
            product.price,
            product.purchase_price,
            product.unit_weight,
            product.current_stock,
            product.minimum_stock,
            product.supplier
        ))

        conn.commit()

        row = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        print("PRODUCT ADDED SUCCESSFULLY")
        print("Product ID:", product_id)
        print("================================\n")

        conn.close()

        return dict(row)

    except Exception as e:

        conn.rollback()

        print("\n========== ADD PRODUCT ERROR ==========")
        print("ERROR TYPE:", type(e).__name__)
        print("ERROR:", str(e))
        print("=======================================\n")

        conn.close()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================
# UPDATE PRODUCT
# PUT /products/{product_id}
# =========================

@app.put("/products/{product_id}")
def update_product(product_id: str, product: ProductCreate):

    conn = get_connection()

    cursor = conn.execute("""
        UPDATE products
        SET
            name = ?,
            category = ?,
            rfid_tag = ?,
            price = ?,
            purchase_price = ?,
            unit_weight = ?,
            current_stock = ?,
            minimum_stock = ?,
            supplier = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        product.name,
        product.category,
        product.rfid_tag,
        product.price,
        product.purchase_price,
        product.unit_weight,
        product.current_stock,
        product.minimum_stock,
        product.supplier,
        product_id
    ))

    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    row = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    conn.close()

    return dict(row)


# =========================
# DELETE PRODUCT
# DELETE /products/{product_id}
# =========================

@app.delete("/products/{product_id}")
def delete_product(product_id: str):

    conn = get_connection()

    cursor = conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    conn.close()

    return {
        "status": "success",
        "message": "Product deleted successfully"
    }


# =========================
# GET ALL TROLLEYS
# =========================

@app.get("/trolleys")
def get_trolleys():

    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM trolleys
        ORDER BY trolley_number
    """).fetchall()

    conn.close()

    trolleys = [
        dict(row)
        for row in rows
    ]

    return {
        "count": len(trolleys),
        "trolleys": trolleys
    }


# =========================
# TROLLEY DATA MODEL
# =========================

class TrolleyCreate(BaseModel):
    trolley_number: str
    status: str
    firmware_version: str


# =========================
# CREATE TROLLEY
# POST /trolleys
# =========================

@app.post("/trolleys")
def create_trolley(trolley: TrolleyCreate):

    conn = get_connection()
    trolley_id = str(uuid.uuid4())

    cursor = conn.execute("""
        INSERT INTO trolleys (
            id,
            trolley_number,
            status,
            firmware_version
        )
        VALUES (?, ?, ?, ?)
    """, (
        trolley_id,
        trolley.trolley_number,
        trolley.status,
        trolley.firmware_version
    ))

    conn.commit()

    row = conn.execute(
        "SELECT * FROM trolleys WHERE id = ?",
        (trolley_id,)
    ).fetchone()

    conn.close()

    return dict(row)
# =========================
# CART ITEM DATA MODEL
# =========================

class CartItemCreate(BaseModel):
    trolley_id: str
    product_id: str
    quantity: int
    expected_weight: float
    actual_weight: float
    verified: bool

class VerifyCartItem(BaseModel):
    trolley_id: str
    product_id: str
    actual_weight: float
    quantity: int = 1

class UpdateAlertStatus(BaseModel):
    status: str

class CheckoutRequest(BaseModel):
    trolley_id: str
    payment_status: str  

class StockOrderCreate(BaseModel):
    supplier: str
    expected_date: str | None = None


class StockOrderItemCreate(BaseModel):
    order_id: str
    product_id: str
    quantity_ordered: int
    purchase_price: float     

class ReceiveStockRequest(BaseModel):
    order_item_id: str
    quantity_received: int
# =========================
# STOCK ORDERS
# =========================



@app.post("/stock-orders")
def create_stock_order(order: StockOrderCreate):

    conn = get_connection()

    try:
        # Generate UUID for stock order
        order_id = str(uuid.uuid4())

        cursor = conn.execute("""
            INSERT INTO stock_orders (
                id,
                supplier,
                expected_date,
                status
            )
            VALUES (?, ?, ?, ?)
        """, (
            order_id,
            order.supplier,
            order.expected_date,
            "pending"
        ))

        conn.commit()

        row = conn.execute("""
            SELECT *
            FROM stock_orders
            WHERE id = ?
        """, (order_id,)).fetchone()

        if not row:
            return {
                "status": "error",
                "message": "Stock order could not be created"
            }

        return {
            "status": "created",
            "message": "Stock order created successfully",
            "order": dict(row)
        }

    except Exception as e:
        conn.rollback()

        print("Create stock order error:", e)

        return {
            "status": "error",
            "message": "Stock order could not be created"
        }

    finally:
        conn.close()



# =========================
# CHECKOUT
# POST /checkout
# =========================

@app.post("/checkout")
def checkout(request: CheckoutRequest):

    conn = get_connection()

    try:

        # =====================================================
        # 0. CHECK TROLLEY
        # =====================================================

        trolley = conn.execute("""
            SELECT *
            FROM trolleys
            WHERE id = ?
        """, (request.trolley_id,)).fetchone()

        if not trolley:
            return {
                "status": "not_found",
                "message": "Trolley not found"
            }

        # =====================================================
        # 1. PAYMENT MUST BE SUCCESSFUL
        # =====================================================

        if request.payment_status != "paid":
            return {
                "status": "payment_required",
                "message": "Checkout allowed only after successful payment"
            }

        # =====================================================
        # 2. GET CART
        # =====================================================

        cart_rows = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE trolley_id = ?
        """, (request.trolley_id,)).fetchall()

        cart_items = [
            dict(row)
            for row in cart_rows
        ]

        if not cart_items:
            return {
                "status": "empty_cart",
                "message": "No items found in trolley"
            }

        # =====================================================
        # 3. ALL ITEMS MUST BE VERIFIED
        # =====================================================

        unverified_items = [
            item
            for item in cart_items
            if not item["verified"]
        ]

        if unverified_items:
            return {
                "status": "verification_required",
                "message": "All cart items must be verified before checkout"
            }

        # =====================================================
        # 4. CALCULATE TOTAL + PREPARE ITEMS
        # =====================================================

        total_amount = 0
        transaction_items = []

        for item in cart_items:

            product = conn.execute("""
                SELECT *
                FROM products
                WHERE id = ?
            """, (item["product_id"],)).fetchone()

            if not product:
                return {
                    "status": "product_not_found",
                    "message": f"Product not found: {item['product_id']}"
                }

            product = dict(product)

            quantity = int(item["quantity"])
            unit_price = float(product["price"])
            item_total = unit_price * quantity

            # Check stock
            current_stock = int(product["current_stock"])

            if current_stock < quantity:
                return {
                    "status": "insufficient_stock",
                    "message": (
                        f"Insufficient stock for {product['name']}. "
                        f"Available: {current_stock}, "
                        f"Required: {quantity}"
                    )
                }

            total_amount += item_total

            transaction_items.append({
                "product_id": product["id"],
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": item_total
            })

        # =====================================================
        # 5. GENERATE TRANSACTION UUID
        # =====================================================

        transaction_id = str(uuid.uuid4())

        # =====================================================
        # 6. CREATE TRANSACTION
        # =====================================================

        conn.execute("""
            INSERT INTO transactions (
                id,
                trolley_id,
                total_amount,
                payment_status
            )
            VALUES (?, ?, ?, ?)
        """, (
            transaction_id,
            request.trolley_id,
            total_amount,
            "paid"
        ))

        # =====================================================
        # 7. ADD TRANSACTION ITEMS
        # =====================================================

        for item in transaction_items:

            transaction_item_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO transaction_items (
                    id,
                    transaction_id,
                    product_id,
                    quantity,
                    unit_price,
                    total_price
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transaction_item_id,
                transaction_id,
                item["product_id"],
                item["quantity"],
                item["unit_price"],
                item["total_price"]
            ))

        # =====================================================
        # 8. DEDUCT INVENTORY + CREATE SALE MOVEMENT
        # =====================================================

        for item in transaction_items:

            product = conn.execute("""
                SELECT current_stock
                FROM products
                WHERE id = ?
            """, (item["product_id"],)).fetchone()

            if not product:
                raise Exception(
                    f"Product not found during stock update: "
                    f"{item['product_id']}"
                )

            current_stock = int(product["current_stock"])

            new_stock = current_stock - item["quantity"]

            conn.execute("""
                UPDATE products
                SET
                    current_stock = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                new_stock,
                item["product_id"]
            ))

            # Generate inventory movement UUID
            movement_id = str(uuid.uuid4())

            # Record SALE movement
            conn.execute("""
                INSERT INTO inventory_movements (
                    id,
                    product_id,
                    type,
                    quantity,
                    reference_id
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                movement_id,
                item["product_id"],
                "SALE",
                item["quantity"],
                transaction_id
            ))

        # =====================================================
        # 9. CLEAR CART
        # =====================================================

        conn.execute("""
            DELETE FROM cart_items
            WHERE trolley_id = ?
        """, (request.trolley_id,))

        # =====================================================
        # 10. MAKE TROLLEY AVAILABLE
        # =====================================================

        conn.execute("""
            UPDATE trolleys
            SET
                status = 'available',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (request.trolley_id,))

        # =====================================================
        # 11. COMMIT EVERYTHING
        # =====================================================

        conn.commit()

        return {
            "status": "success",
            "message": "Checkout completed successfully",
            "transaction_id": transaction_id,
            "total_amount": total_amount,
            "items_count": len(cart_items),
            "trolley_status": "available"
        }

    except Exception as e:

        conn.rollback()

        print("Checkout error:", e)

        return {
            "status": "error",
            "message": "Checkout could not be completed"
        }

    finally:

        conn.close()

# =========================
# UPDATE ALERT STATUS
# PUT /alerts/{alert_id}
# =========================

@app.put("/alerts/{alert_id}")
def update_alert_status(alert_id: str, alert: UpdateAlertStatus):

    # Only these statuses are allowed
    if alert.status not in ["active", "resolved", "dismissed"]:
        return {
            "status": "invalid",
            "message": "Status must be active, resolved, or dismissed"
        }

    conn = get_connection()

    try:

        # Check alert exists
        existing_alert = conn.execute("""
            SELECT *
            FROM alerts
            WHERE id = ?
        """, (alert_id,)).fetchone()

        if not existing_alert:
            return {
                "status": "not_found",
                "message": "Alert not found"
            }

        # Set resolved time when resolved/dismissed
        resolved_at = None

        if alert.status in ["resolved", "dismissed"]:
            from datetime import datetime, timezone
            resolved_at = datetime.now(timezone.utc).isoformat()

        # Update alert
        conn.execute("""
            UPDATE alerts
            SET
                status = ?,
                resolved_at = ?
            WHERE id = ?
        """, (
            alert.status,
            resolved_at,
            alert_id
        ))

        conn.commit()

        # Get updated alert
        updated_alert = conn.execute("""
            SELECT *
            FROM alerts
            WHERE id = ?
        """, (alert_id,)).fetchone()

        return {
            "status": "updated",
            "alert": dict(updated_alert)
        }

    except Exception as e:

        conn.rollback()

        print("Alert update error:", e)

        return {
            "status": "error",
            "message": "Alert could not be updated"
        }

    finally:
        conn.close()
# =========================
# LOCAL DATA API ROUTES
# =========================

@app.get("/transactions")
def get_transactions():
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, tr.trolley_number,
               COUNT(ti.id) AS items
        FROM transactions t
        LEFT JOIN trolleys tr ON tr.id = t.trolley_id
        LEFT JOIN transaction_items ti ON ti.transaction_id = t.id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/inventory-movements")
def get_inventory_movements(type: str | None = None):
    conn = get_connection()
    if type:
        rows = conn.execute("""
            SELECT im.*, p.name AS product_name
            FROM inventory_movements im
            LEFT JOIN products p ON p.id = im.product_id
            WHERE im.type = ?
            ORDER BY im.created_at DESC
        """, (type,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT im.*, p.name AS product_name
            FROM inventory_movements im
            LEFT JOIN products p ON p.id = im.product_id
            ORDER BY im.created_at DESC
        """).fetchall()
    conn.close()
    result=[]
    for r in rows:
        d=dict(r)
        d["products"]={"name":d.pop("product_name",None)}
        result.append(d)
    return result

@app.get("/alerts")
def get_alerts(include_resolved: bool = True):
    conn=get_connection()
    query="""
        SELECT a.*, tr.trolley_number, p.name AS product_name
        FROM alerts a
        LEFT JOIN trolleys tr ON tr.id=a.trolley_id
        LEFT JOIN products p ON p.id=a.product_id
    """
    params=()
    if not include_resolved:
        query += " WHERE a.status != 'resolved' "
    query += " ORDER BY a.created_at DESC"
    rows=conn.execute(query,params).fetchall()
    conn.close()
    result=[]
    for r in rows:
        d=dict(r)
        d["trolleys"]={"trolley_number":d.pop("trolley_number",None)}
        d["products"]={"name":d.pop("product_name",None)}
        result.append(d)
    return result

@app.put("/trolleys/{trolley_id}")
def update_trolley(trolley_id: str, payload: dict):
    status=payload.get("status")
    allowed=["available","shopping","alert","checkout","offline"]
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid trolley status")
    conn=get_connection()
    cur=conn.execute("""
        UPDATE trolleys SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
    """,(status,trolley_id))
    conn.commit()
    row=conn.execute("SELECT * FROM trolleys WHERE id=?",(trolley_id,)).fetchone()
    conn.close()
    if cur.rowcount==0 or not row:
        raise HTTPException(status_code=404, detail="Trolley not found")
    return dict(row)

@app.get("/stock-orders")
def get_stock_orders():
    conn=get_connection()
    rows=conn.execute("""
        SELECT so.*, soi.id AS item_id, soi.product_id, soi.quantity_ordered,
               soi.quantity_received, soi.purchase_price, p.name AS product_name
        FROM stock_orders so
        LEFT JOIN stock_order_items soi ON soi.order_id=so.id
        LEFT JOIN products p ON p.id=soi.product_id
        ORDER BY so.order_date DESC
    """).fetchall()
    conn.close()
    result=[]
    for r in rows:
        d=dict(r)
        item={
            "id":d.pop("item_id",None),
            "product_id":d.pop("product_id",None),
            "quantity_ordered":d.pop("quantity_ordered",0) or 0,
            "quantity_received":d.pop("quantity_received",0) or 0,
            "purchase_price":d.pop("purchase_price",0) or 0,
            "products":{"name":d.pop("product_name",None)}
        }
        d["stock_order_items"]=[] if item["id"] is None else [item]
        result.append(d)
    return result

@app.post("/stock-order-items")
def create_stock_order_item(item: StockOrderItemCreate):
    conn=get_connection()
    item_id=str(uuid.uuid4())
    try:
        conn.execute("""
            INSERT INTO stock_order_items
            (id, order_id, product_id, quantity_ordered, quantity_received, purchase_price)
            VALUES (?, ?, ?, ?, 0, ?)
        """,(item_id,item.order_id,item.product_id,item.quantity_ordered,item.purchase_price))
        conn.commit()
        row=conn.execute("SELECT * FROM stock_order_items WHERE id=?",(item_id,)).fetchone()
        return dict(row)
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=400,detail=str(e))
    finally: conn.close()

@app.post("/receive-stock")
def receive_stock(request: ReceiveStockRequest):
    conn=get_connection()
    try:
        item=conn.execute("SELECT * FROM stock_order_items WHERE id=?",(request.order_item_id,)).fetchone()
        if not item: raise HTTPException(status_code=404,detail="Order item not found")
        item=dict(item)
        remaining=int(item["quantity_ordered"])-int(item["quantity_received"] or 0)
        qty=int(request.quantity_received)
        if qty<=0 or qty>remaining: raise HTTPException(status_code=400,detail=f"Only {remaining} units are remaining")
        new_received=int(item["quantity_received"] or 0)+qty
        new_status="received" if new_received>=int(item["quantity_ordered"]) else "partially_received"
        conn.execute("UPDATE stock_order_items SET quantity_received=? WHERE id=?",(new_received,item["id"]))
        conn.execute("UPDATE stock_orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",(new_status,item["order_id"]))
        conn.execute("UPDATE products SET current_stock=current_stock+?, updated_at=CURRENT_TIMESTAMP WHERE id=?",(qty,item["product_id"]))
        conn.execute("""INSERT INTO inventory_movements (id,product_id,type,quantity,reference_id) VALUES (?,?,?,?,?)""",(str(uuid.uuid4()),item["product_id"],"PURCHASE",qty,item["order_id"]))
        conn.commit()
        order=conn.execute("SELECT * FROM stock_orders WHERE id=?",(item["order_id"],)).fetchone()
        return {"status":"success","order":dict(order),"item":dict(conn.execute("SELECT * FROM stock_order_items WHERE id=?",(item["id"],)).fetchone())}
    except HTTPException: conn.rollback(); raise
    except Exception as e: conn.rollback(); print("Receive stock error:",e); raise HTTPException(status_code=500,detail="Receive stock failed")
    finally: conn.close()

# =========================
# VERIFY CART ITEM
# POST /verify-cart-item
# =========================

@app.post("/verify-cart-item")
def verify_cart_item(item: VerifyCartItem):

    conn = get_connection()

    try:

        # =====================================================
        # 0. CHECK TROLLEY
        # =====================================================

        trolley = conn.execute("""
            SELECT *
            FROM trolleys
            WHERE id = ?
        """, (item.trolley_id,)).fetchone()

        if not trolley:
            return {
                "status": "not_found",
                "message": "Trolley not found"
            }

        # =====================================================
        # 1. GET PRODUCT
        # =====================================================

        product = conn.execute("""
            SELECT *
            FROM products
            WHERE id = ?
        """, (item.product_id,)).fetchone()

        if not product:
            return {
                "status": "not_found",
                "message": "Product not found"
            }

        product = dict(product)

        # =====================================================
        # 2. VALIDATE UNIT WEIGHT
        # =====================================================

        if (
            product["unit_weight"] is None
            or float(product["unit_weight"]) <= 0
        ):
            return {
                "status": "invalid",
                "message": "Product unit weight must be greater than 0"
            }

        # =====================================================
        # 3. CALCULATE EXPECTED WEIGHT
        # =====================================================

        unit_weight = float(product["unit_weight"])

        expected_weight = (
            unit_weight * item.quantity
        )

        # =====================================================
        # 4. CALCULATE DIFFERENCE
        # =====================================================

        difference_percent = (
            abs(item.actual_weight - expected_weight)
            / expected_weight
        ) * 100

        # =====================================================
        # 5. 5% TOLERANCE
        # =====================================================

        verified = difference_percent <= 5

        # =====================================================
        # 6. VERIFIED → ADD TO CART
        # =====================================================

        if verified:

            cursor = conn.execute("""
                INSERT INTO cart_items (
                    trolley_id,
                    product_id,
                    quantity,
                    expected_weight,
                    actual_weight,
                    verified
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item.trolley_id,
                item.product_id,
                item.quantity,
                expected_weight,
                item.actual_weight,
                True
            ))

            conn.commit()

            cart_item = conn.execute("""
                SELECT *
                FROM cart_items
                WHERE rowid = ?
            """, (cursor.lastrowid,)).fetchone()

            return {
                "status": "verified",
                "verified": True,
                "expected_weight": expected_weight,
                "actual_weight": item.actual_weight,
                "difference_percent": round(
                    difference_percent,
                    2
                ),
                "product": product,
                "cart_item": dict(cart_item)
            }

        # =====================================================
        # 7. MISMATCH → CREATE ALERT
        # =====================================================

        alert_cursor = conn.execute("""
            INSERT INTO alerts (
                trolley_id,
                product_id,
                type,
                expected_value,
                actual_value,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            item.trolley_id,
            item.product_id,
            "weight_mismatch",
            expected_weight,
            item.actual_weight,
            "active"
        ))

        conn.commit()

        alert = conn.execute("""
            SELECT *
            FROM alerts
            WHERE id = ?
        """, (alert_cursor.lastrowid,)).fetchone()

        return {
            "status": "mismatch",
            "verified": False,
            "expected_weight": expected_weight,
            "actual_weight": item.actual_weight,
            "difference_percent": round(
                difference_percent,
                2
            ),
            "message": "Weight mismatch. Verification required.",
            "alert": dict(alert) if alert else None
        }

    except Exception as e:

        conn.rollback()

        print("Verify cart item error:", e)

        return {
            "status": "error",
            "message": "Cart item verification failed"
        }

    finally:
        conn.close()
# =========================
# GET CART ITEMS
# GET /cart-items
# =========================
@app.get("/cart-items")
def get_cart_items():

    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                ci.id,
                ci.trolley_id,
                ci.product_id,
                ci.quantity,
                ci.expected_weight,
                ci.actual_weight,
                ci.verified,

                p.name AS product_name,
                p.price AS product_price

            FROM cart_items ci

            LEFT JOIN products p
                ON p.id = ci.product_id

            ORDER BY ci.rowid DESC
        """).fetchall()

        cart_items = []

        for row in rows:

            item = dict(row)

            item["products"] = {
                "id": item["product_id"],
                "name": item["product_name"],
                "price": item["product_price"]
            }

            del item["product_name"]
            del item["product_price"]

            cart_items.append(item)

        return cart_items

    except Exception as e:

        print("Get cart items error:", e)

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch cart items"
        )

    finally:
        conn.close()
# =========================
# ADD ITEM TO CART
# POST /cart-items
# =========================

@app.post("/cart-items")
def add_cart_item(item: CartItemCreate):

    conn = get_connection()

    try:

        # Check trolley exists
        trolley = conn.execute("""
            SELECT id
            FROM trolleys
            WHERE id = ?
        """, (item.trolley_id,)).fetchone()

        if not trolley:
            return {
                "status": "not_found",
                "message": "Trolley not found"
            }

        # Check product exists
        product = conn.execute("""
            SELECT id
            FROM products
            WHERE id = ?
        """, (item.product_id,)).fetchone()

        if not product:
            return {
                "status": "not_found",
                "message": "Product not found"
            }

        # Generate unique cart item ID
        cart_item_id = str(uuid.uuid4())

        # Add cart item
        conn.execute("""
            INSERT INTO cart_items (
                id,
                trolley_id,
                product_id,
                quantity,
                expected_weight,
                actual_weight,
                verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cart_item_id,
            item.trolley_id,
            item.product_id,
            item.quantity,
            item.expected_weight,
            item.actual_weight,
            item.verified
        ))

        conn.commit()

        # Get newly created cart item
        cart_item = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE id = ?
        """, (cart_item_id,)).fetchone()

        return {
            "status": "added",
            "cart_item": dict(cart_item)
        }

    except Exception as e:

        conn.rollback()

        print("Add cart item error:", e)

        return {
            "status": "error",
            "message": "Cart item could not be added"
        }

    finally:
        conn.close()

@app.post("/payment/create-qr")
def create_payment_qr(data: PaymentCreate):

    conn = get_connection()

    try:

        rows = conn.execute("""
            SELECT
                ci.quantity,
                p.name,
                p.price
            FROM cart_items ci
            JOIN products p
                ON ci.product_id = p.id
            WHERE ci.trolley_id = ?
        """, (data.trolley_id,)).fetchall()

    finally:
        conn.close()

    # ==============================
    # CHECK CART
    # ==============================

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Cart is empty"
        )

    # ==============================
    # CALCULATE CART TOTAL
    # ==============================

    total = sum(
        float(row["price"]) * int(row["quantity"])
        for row in rows
    )

    if total <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid cart total"
        )

    amount_paise = int(round(total * 100))

    # ==============================
    # QR EXPIRY = 30 MINUTES
    # ==============================

    import time

    close_by = int(time.time()) + (30 * 60)

    # ==============================
    # CREATE RAZORPAY DYNAMIC QR
    # ==============================

    try:

        response = requests.post(
            "https://api.razorpay.com/v1/payments/qr_codes",

            auth=(
                RAZORPAY_KEY_ID,
                RAZORPAY_KEY_SECRET
            ),

            json={
                "type": "upi_qr",

                "name": "RETROIQ Cart Payment",

                "usage": "single_use",

                "fixed_amount": True,

                "payment_amount": amount_paise,

                "description": (
                    f"RETROIQ Cart Payment - ₹{total:.2f}"
                ),

                "close_by": close_by,

                "notes": {
                    "trolley_id": data.trolley_id,
                    "source": "RETROIQ"
                }
            },

            timeout=20
        )

        # ==============================
        # RAZORPAY API ERROR
        # ==============================

        if not response.ok:

            print(
                "RAZORPAY STATUS:",
                response.status_code
            )

            print(
                "RAZORPAY RESPONSE:",
                response.text
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Razorpay API error: "
                    f"{response.text}"
                )
            )

        # ==============================
        # GET QR RESPONSE
        # ==============================

        qr = response.json()

        # ==============================
        # SUCCESS RESPONSE
        # ==============================

        return {

            "success": True,

            "payment_method": "RAZORPAY",

            "qr_id": qr["id"],

            "image_url": qr["image_url"],

            "amount": total,

            "amount_paise": amount_paise,

            "status": qr["status"],

            "close_by": qr["close_by"]

        }

    # ==============================
    # FASTAPI HTTP ERROR
    # ==============================

    except HTTPException:
        raise

    # ==============================
    # OTHER ERROR
    # ==============================

    except Exception as e:

        print(
            "Razorpay QR error:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to create payment QR: "
                f"{str(e)}"
            )
        )


# =========================================================
# RAZORPAY WEBHOOK
# POST /webhook/razorpay
# =========================================================

RAZORPAY_WEBHOOK_SECRET = os.getenv(
    "RAZORPAY_WEBHOOK_SECRET"
)


@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):

    # -----------------------------------------------------
    # 1. READ RAW BODY
    # -----------------------------------------------------

    raw_body = await request.body()

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    if not signature:

        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay signature"
        )


    # -----------------------------------------------------
    # 2. CHECK WEBHOOK SECRET
    # -----------------------------------------------------

    if not RAZORPAY_WEBHOOK_SECRET:

        print(
            "RAZORPAY_WEBHOOK_SECRET is missing"
        )

        raise HTTPException(
            status_code=500,
            detail="Webhook secret not configured"
        )


    # -----------------------------------------------------
    # 3. VERIFY SIGNATURE
    # -----------------------------------------------------

    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()


    if not hmac.compare_digest(
        signature,
        expected_signature
    ):

        print(
            "Invalid Razorpay webhook signature"
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature"
        )


    # -----------------------------------------------------
    # 4. PARSE JSON
    # -----------------------------------------------------

    try:

        payload = json.loads(
            raw_body.decode("utf-8")
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook JSON"
        )


    event = payload.get("event")


    print("\n========== RAZORPAY WEBHOOK ==========")
    print("Event:", event)


    # -----------------------------------------------------
    # 5. IGNORE OTHER EVENTS
    # -----------------------------------------------------

    if event != "payment.captured":

        return {
            "status": "ignored",
            "event": event
        }


    # -----------------------------------------------------
    # 6. GET PAYMENT DATA
    # -----------------------------------------------------

    try:

        payment = (
            payload
            ["payload"]
            ["payment"]
            ["entity"]
        )

    except (KeyError, TypeError):

        raise HTTPException(
            status_code=400,
            detail="Invalid payment payload"
        )


    payment_id = payment.get("id")

    payment_amount = int(
        payment.get("amount", 0)
    )

    payment_status = payment.get(
        "status"
    )


    print("Payment ID:", payment_id)
    print("Amount:", payment_amount)
    print("Status:", payment_status)


    # -----------------------------------------------------
    # 7. PAYMENT MUST BE CAPTURED
    # -----------------------------------------------------

    if payment_status != "captured":

        return {
            "status": "ignored",
            "message": "Payment is not captured"
        }


    # -----------------------------------------------------
    # 8. GET TROLLEY FROM PAYMENT NOTES
    # -----------------------------------------------------

    notes = payment.get(
        "notes",
        {}
    )

    trolley_id = notes.get(
        "trolley_id"
    )


    if not trolley_id:

        print(
            "Trolley ID missing in payment notes"
        )

        raise HTTPException(
            status_code=400,
            detail="Trolley ID missing"
        )


    # -----------------------------------------------------
    # 9. CHECK CART TOTAL
    # -----------------------------------------------------

    conn = get_connection()

    try:

        rows = conn.execute("""
            SELECT
                ci.quantity,
                p.price
            FROM cart_items ci
            JOIN products p
                ON ci.product_id = p.id
            WHERE ci.trolley_id = ?
        """, (
            trolley_id,
        )).fetchall()


        if not rows:

            return {
                "status": "already_processed",
                "message": "Cart is already empty"
            }


        cart_total = sum(
            float(row["price"])
            * int(row["quantity"])
            for row in rows
        )


        expected_amount = int(
            round(cart_total * 100)
        )


    finally:

        conn.close()


    # -----------------------------------------------------
    # 10. PAYMENT AMOUNT MUST MATCH CART
    # -----------------------------------------------------

    if payment_amount != expected_amount:

        print(
            "PAYMENT AMOUNT MISMATCH"
        )

        print(
            "Expected:",
            expected_amount
        )

        print(
            "Received:",
            payment_amount
        )

        raise HTTPException(
            status_code=400,
            detail="Payment amount does not match cart"
        )


    # -----------------------------------------------------
    # 11. COMPLETE CHECKOUT
    # -----------------------------------------------------

    checkout_result = checkout(
        CheckoutRequest(
            trolley_id=trolley_id,
            payment_status="paid"
        )
    )


    print(
        "Checkout result:",
        checkout_result
    )


    # -----------------------------------------------------
    # 12. RETURN SUCCESS
    # -----------------------------------------------------

    if checkout_result.get(
        "status"
    ) == "success":

        return {
            "status": "success",
            "message": "Payment verified and checkout completed",
            "payment_id": payment_id,
            "transaction_id":
                checkout_result.get(
                    "transaction_id"
                )
        }


    # -----------------------------------------------------
    # CHECKOUT FAILED
    # -----------------------------------------------------

    return {
        "status": "checkout_failed",
        "message": checkout_result.get(
            "message",
            "Checkout failed"
        )
    }    
# =========================
# UPDATE CART ITEM QUANTITY
# PUT /cart-items/{cart_item_id}
# =========================

class CartItemQuantityUpdate(BaseModel):
    quantity: int


@app.put("/cart-items/{cart_item_id}")
def update_cart_item_quantity(
    cart_item_id: str,
    item: CartItemQuantityUpdate
):
    conn = get_connection()

    try:
        # Quantity must be at least 1
        if item.quantity < 1:
            return {
                "status": "invalid",
                "message": "Quantity must be at least 1"
            }

        # Check cart item
        cart_item = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE id = ?
        """, (cart_item_id,)).fetchone()

        if not cart_item:
            return {
                "status": "not_found",
                "message": "Cart item not found"
            }

        # Update quantity
        conn.execute("""
            UPDATE cart_items
            SET quantity = ?
            WHERE id = ?
        """, (
            item.quantity,
            cart_item_id
        ))

        conn.commit()

        # Get updated cart item
        updated_item = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE id = ?
        """, (cart_item_id,)).fetchone()

        return {
            "status": "updated",
            "message": "Cart quantity updated successfully",
            "cart_item": dict(updated_item)
        }

    except Exception as e:
        conn.rollback()

        print("Update cart item error:", e)

        return {
            "status": "error",
            "message": "Cart quantity could not be updated"
        }

    finally:
        conn.close()
# =========================
# DELETE CART ITEM
# DELETE /cart-items/{cart_item_id}
# =========================

@app.delete("/cart-items/{cart_item_id}")
def delete_cart_item(cart_item_id: str):

    conn = get_connection()

    try:

        # Check cart item exists
        cart_item = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE id = ?
        """, (cart_item_id,)).fetchone()

        if not cart_item:
            return {
                "status": "not_found",
                "message": "Cart item not found"
            }

        # Delete cart item
        conn.execute("""
            DELETE FROM cart_items
            WHERE id = ?
        """, (cart_item_id,))

        # Make trolley available when its last cart item is removed
        remaining_items = conn.execute("""
            SELECT COUNT(*)
            FROM cart_items
            WHERE trolley_id = ?
        """, (cart_item["trolley_id"],)).fetchone()[0]

        if remaining_items == 0:
            conn.execute("""
                UPDATE trolleys
                SET status = 'available'
                WHERE id = ?
            """, (cart_item["trolley_id"],))

        conn.commit()

        return {
            "status": "removed",
            "cart_item": dict(cart_item)
        }

    except Exception as e:

        conn.rollback()

        print("Delete cart item error:", e)

        return {
            "status": "error",
            "message": "Cart item could not be removed"
        }

    finally:
        conn.close()
# =========================
# FIND PRODUCT BY RFID
# GET /products/rfid/{rfid_tag}
# =========================

@app.get("/products/rfid/{rfid_tag}")
def get_product_by_rfid(rfid_tag: str):

    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM products
        WHERE rfid_tag = ?
    """, (rfid_tag,)).fetchone()

    conn.close()

    if not row:
        return {
            "status": "not_found",
            "message": "No product found for this RFID tag"
        }

    return {
        "status": "found",
        "product": dict(row)
    }   

@app.get("/test-sqlite")
def test_sqlite():

    conn = get_connection()

    result = conn.execute(
        "SELECT COUNT(*) AS count FROM products"
    ).fetchone()

    conn.close()

    return {
        "status": "success",
        "database": "sqlite",
        "products_count": result["count"]
    }        
# =========================
# UPDATE CART ITEM QUANTITY
# PUT /cart-items/{cart_item_id}
# =========================

class CartItemQuantityUpdate(BaseModel):
    quantity: int


@app.put("/cart-items/{cart_item_id}")
def update_cart_item_quantity(
    cart_item_id: str,
    item: CartItemQuantityUpdate
):
    conn = get_connection()

    try:
        # Quantity must be at least 1
        if item.quantity < 1:
            return {
                "status": "invalid",
                "message": "Quantity must be at least 1"
            }

        # Check cart item
        cart_item = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE id = ?
        """, (cart_item_id,)).fetchone()

        if not cart_item:
            return {
                "status": "not_found",
                "message": "Cart item not found"
            }

        # Update quantity
        conn.execute("""
            UPDATE cart_items
            SET quantity = ?
            WHERE id = ?
        """, (
            item.quantity,
            cart_item_id
        ))

        conn.commit()

        # Get updated cart item
        updated_item = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE id = ?
        """, (cart_item_id,)).fetchone()

        return {
            "status": "updated",
            "message": "Cart quantity updated successfully",
            "cart_item": dict(updated_item)
        }

    except Exception as e:
        conn.rollback()

        print("Update cart item error:", e)

        return {
            "status": "error",
            "message": "Cart quantity could not be updated"
        }

    finally:
        conn.close()
# =========================
# DELETE CART ITEM
# DELETE /cart-items/{cart_item_id}
# =========================

@app.delete("/cart-items/{cart_item_id}")
def delete_cart_item(cart_item_id: str):

    conn = get_connection()

    try:

        # Check cart item exists
        cart_item = conn.execute("""
            SELECT *
            FROM cart_items
            WHERE id = ?
        """, (cart_item_id,)).fetchone()

        if not cart_item:
            return {
                "status": "not_found",
                "message": "Cart item not found"
            }

        # Delete cart item
        conn.execute("""
            DELETE FROM cart_items
            WHERE id = ?
        """, (cart_item_id,))

        # Make trolley available when its last cart item is removed
        remaining_items = conn.execute("""
            SELECT COUNT(*)
            FROM cart_items
            WHERE trolley_id = ?
        """, (cart_item["trolley_id"],)).fetchone()[0]

        if remaining_items == 0:
            conn.execute("""
                UPDATE trolleys
                SET status = 'available'
                WHERE id = ?
            """, (cart_item["trolley_id"],))

        conn.commit()

        return {
            "status": "removed",
            "cart_item": dict(cart_item)
        }

    except Exception as e:

        conn.rollback()

        print("Delete cart item error:", e)

        return {
            "status": "error",
            "message": "Cart item could not be removed"
        }

    finally:
        conn.close()
# =========================
# FIND PRODUCT BY RFID
# GET /products/rfid/{rfid_tag}
# =========================

@app.get("/products/rfid/{rfid_tag}")
def get_product_by_rfid(rfid_tag: str):

    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM products
        WHERE rfid_tag = ?
    """, (rfid_tag,)).fetchone()

    conn.close()

    if not row:
        return {
            "status": "not_found",
            "message": "No product found for this RFID tag"
        }

    return {
        "status": "found",
        "product": dict(row)
    }   

@app.get("/test-sqlite")
def test_sqlite():

    conn = get_connection()

    result = conn.execute(
        "SELECT COUNT(*) AS count FROM products"
    ).fetchone()

    conn.close()

    return {
        "status": "success",
        "database": "sqlite",
        "products_count": result["count"]
    }        