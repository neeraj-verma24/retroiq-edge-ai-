import itertools
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone


def _dt(value):
    if not value:
        return None
    try:
        v = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _now():
    return datetime.now(timezone.utc)


def _sales_by_product(conn, days=14):
    since = (_now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """
        SELECT
            ti.product_id,
            COALESCE(SUM(ti.quantity), 0) AS units,
            COUNT(DISTINCT ti.transaction_id) AS orders
        FROM transaction_items ti
        JOIN transactions t ON t.id = ti.transaction_id
        WHERE t.payment_status = 'paid'
          AND t.created_at >= ?
        GROUP BY ti.product_id
        """,
        (since,),
    ).fetchall()
    return {str(r["product_id"]): dict(r) for r in rows}


def inventory_intelligence(conn, lookback_days=14, forecast_days=7):
    products = [dict(r) for r in conn.execute(
        "SELECT * FROM products ORDER BY name"
    ).fetchall()]
    sales = _sales_by_product(conn, lookback_days)

    out = []
    for p in products:
        pid = str(p["id"])
        stock = int(p.get("current_stock") or 0)
        minimum = int(p.get("minimum_stock") or 0)
        price = float(p.get("price") or 0)
        purchase_price = float(p.get("purchase_price") or 0)

        s = sales.get(pid, {"units": 0, "orders": 0})
        units = int(s.get("units") or 0)
        daily_velocity = units / max(lookback_days, 1)
        forecast = daily_velocity * forecast_days

        days_to_stockout = (
            stock / daily_velocity if daily_velocity > 0 else None
        )

        if stock <= 0:
            risk = "critical"
        elif days_to_stockout is not None and days_to_stockout <= 1:
            risk = "critical"
        elif stock <= minimum or (
            days_to_stockout is not None and days_to_stockout <= 3
        ):
            risk = "high"
        elif days_to_stockout is not None and days_to_stockout <= 7:
            risk = "medium"
        else:
            risk = "healthy"

        # Seven-day demand + safety buffer.
        safety_stock = max(minimum, math.ceil(daily_velocity * 1.5))
        target_stock = math.ceil(forecast + safety_stock)
        recommended_order = max(0, target_stock - stock)

        forecast_gap = max(0.0, forecast - stock)
        estimated_lost_sales = forecast_gap * price

        slow_moving = (
            stock > max(minimum * 2, 10)
            and daily_velocity < 0.5
        )
        tied_up_capital = max(0.0, stock - math.ceil(forecast)) * purchase_price

        data_quality = (
            "low" if units == 0
            else "medium" if units < 10
            else "good"
        )

        out.append({
            "id": p["id"],
            "name": p["name"],
            "category": p.get("category"),
            "price": price,
            "current_stock": stock,
            "minimum_stock": minimum,
            "units_sold": units,
            "daily_sales_velocity": round(daily_velocity, 3),
            "forecast_7d": round(forecast, 1),
            "days_to_stockout": (
                round(days_to_stockout, 1)
                if days_to_stockout is not None else None
            ),
            "risk": risk,
            "recommended_order_qty": recommended_order,
            "estimated_lost_sales": round(estimated_lost_sales, 2),
            "slow_moving": slow_moving,
            "tied_up_capital": round(tied_up_capital, 2),
            "data_quality": data_quality,
            "explanation": (
                f"7-day forecast is {forecast:.1f} units; "
                f"current stock is {stock}."
            ),
        })

    return out


def revenue_leak_radar(conn):
    inventory = inventory_intelligence(conn)
    leaks = []

    for p in inventory:
        if p["estimated_lost_sales"] > 0:
            leaks.append({
                "type": "stockout_risk",
                "severity": "high" if p["risk"] in ("critical", "high") else "medium",
                "title": f"{p['name']} stockout risk",
                "estimated_impact": p["estimated_lost_sales"],
                "reason": (
                    f"Forecasted demand exceeds available stock by "
                    f"{max(0, p['forecast_7d'] - p['current_stock']):.1f} units."
                ),
            })

        if p["slow_moving"] and p["tied_up_capital"] > 0:
            leaks.append({
                "type": "slow_moving_inventory",
                "severity": "medium",
                "title": f"{p['name']} slow-moving inventory",
                "estimated_impact": p["tied_up_capital"],
                "reason": (
                    f"Approximately ₹{p['tied_up_capital']:.0f} of purchase "
                    f"capital is tied up above forecast demand."
                ),
            })

    alert_count = conn.execute(
        "SELECT COUNT(*) AS c FROM alerts WHERE status = 'active'"
    ).fetchone()["c"]

    if alert_count:
        leaks.append({
            "type": "guardian_alerts",
            "severity": "medium",
            "title": "Active Retail Guardian events",
            "estimated_impact": 0,
            "reason": f"{alert_count} active verification/anomaly events require review.",
        })

    leaks.sort(key=lambda x: (x["severity"] != "high", -x["estimated_impact"]))
    total = sum(float(x["estimated_impact"]) for x in leaks)

    return {
        "estimated_exposure": round(total, 2),
        "items": leaks[:10],
        "active_guardian_alerts": int(alert_count),
    }


def shopper_intelligence(conn, lookback_days=30):
    since = (_now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d %H:%M:%S")

    tx = conn.execute(
        """
        SELECT id, trolley_id, total_amount, created_at
        FROM transactions
        WHERE payment_status = 'paid' AND created_at >= ?
        ORDER BY created_at
        """,
        (since,),
    ).fetchall()

    avg_basket = (
        sum(float(r["total_amount"] or 0) for r in tx) / len(tx)
        if tx else 0
    )

    basket_sizes = conn.execute(
        """
        SELECT ti.transaction_id, SUM(ti.quantity) AS units
        FROM transaction_items ti
        JOIN transactions t ON t.id = ti.transaction_id
        WHERE t.payment_status = 'paid' AND t.created_at >= ?
        GROUP BY ti.transaction_id
        """,
        (since,),
    ).fetchall()

    avg_items = (
        sum(int(r["units"] or 0) for r in basket_sizes) / len(basket_sizes)
        if basket_sizes else 0
    )

    pair_counter = Counter()
    rows = conn.execute(
        """
        SELECT ti.transaction_id, p.name
        FROM transaction_items ti
        JOIN transactions t ON t.id = ti.transaction_id
        JOIN products p ON p.id = ti.product_id
        WHERE t.payment_status = 'paid' AND t.created_at >= ?
        ORDER BY ti.transaction_id
        """,
        (since,),
    ).fetchall()

    by_tx = defaultdict(list)
    for r in rows:
        by_tx[str(r["transaction_id"])].append(r["name"])

    for names in by_tx.values():
        for a, b in itertools.combinations(sorted(set(names)), 2):
            pair_counter[(a, b)] += 1

    top_pairs = [
        {"products": [a, b], "transactions": count}
        for (a, b), count in pair_counter.most_common(8)
    ]

    # Optional anonymous sensor/event analytics.
    events = []
    try:
        events = [
            dict(r) for r in conn.execute(
                """
                SELECT event_type, session_id, zone_id, value, created_at
                FROM ai_events
                WHERE created_at >= ?
                ORDER BY created_at
                """,
                (since,),
            ).fetchall()
        ]
    except sqlite3.OperationalError:
        pass

    zone_visits = Counter()
    dwell_by_zone = defaultdict(list)
    open_entries = {}
    for e in events:
        sid = e.get("session_id")
        zone = e.get("zone_id") or "unknown"
        et = e.get("event_type")
        if et == "zone_enter":
            zone_visits[zone] += 1
            if sid:
                open_entries[(sid, zone)] = _dt(e.get("created_at"))
        elif et == "zone_exit" and sid:
            start = open_entries.pop((sid, zone), None)
            end = _dt(e.get("created_at"))
            if start and end:
                dwell = max(0, (end - start).total_seconds())
                dwell_by_zone[zone].append(dwell)

    avg_dwell = {
        z: round(sum(v) / len(v), 1)
        for z, v in dwell_by_zone.items() if v
    }

    return {
        "sessions": len(tx),
        "avg_basket_value": round(avg_basket, 2),
        "avg_items_per_basket": round(avg_items, 2),
        "top_product_pairs": top_pairs,
        "zone_activity": [
            {
                "zone": z,
                "visits": count,
                "avg_dwell_seconds": avg_dwell.get(z),
            }
            for z, count in zone_visits.most_common(10)
        ],
        "analytics_mode": (
            "transaction + anonymous sensor events"
            if events
            else "transaction-derived shopper proxy"
        ),
        "data_note": (
            "True person footfall/visual heatmaps require a dedicated "
            "non-camera people/zone sensor layer."
        ),
    }


def queue_intelligence(conn, horizon_minutes=15):
    now = _now()
    since = now - timedelta(hours=2)
    since_sql = since.strftime("%Y-%m-%d %H:%M:%S")

    try:
        events = [
            dict(r) for r in conn.execute(
                """
                SELECT *
                FROM ai_events
                WHERE created_at >= ?
                  AND event_type IN
                    ('queue_join','queue_complete','checkout_start','checkout_complete')
                ORDER BY created_at
                """,
                (since_sql,),
            ).fetchall()
        ]
    except sqlite3.OperationalError:
        events = []

    active_sessions = set()
    arrivals = 0
    completions = 0
    service_times = []

    starts = {}
    for e in events:
        sid = e.get("session_id") or e.get("trolley_id") or e.get("id")
        et = e.get("event_type")
        if et in ("queue_join", "checkout_start"):
            arrivals += 1
            active_sessions.add(str(sid))
            starts[str(sid)] = _dt(e.get("created_at"))
        elif et in ("queue_complete", "checkout_complete"):
            completions += 1
            active_sessions.discard(str(sid))
            st = starts.get(str(sid))
            en = _dt(e.get("created_at"))
            if st and en:
                service_times.append(max(0, (en - st).total_seconds()))

    # Current checkout trolleys are a useful local proxy even without queue sensors.
    checkout_carts = conn.execute(
        "SELECT COUNT(*) AS c FROM trolleys WHERE status = 'checkout'"
    ).fetchone()["c"]

    avg_service = (
        sum(service_times) / len(service_times)
        if service_times else None
    )

    observed_arrival_rate = arrivals / 2.0  # customers/hour over the 2h window
    projected = arrivals - completions
    if observed_arrival_rate > 0:
        projected += observed_arrival_rate * (horizon_minutes / 60.0)

    return {
        "current_waiting_proxy": max(0, len(active_sessions)),
        "active_checkout_carts": int(checkout_carts),
        "arrivals_last_2h": arrivals,
        "completions_last_2h": completions,
        "observed_arrival_rate_per_hour": round(observed_arrival_rate, 2),
        "avg_service_seconds": (
            round(avg_service, 1) if avg_service is not None else None
        ),
        "predicted_load_in_15min": max(0, round(projected, 1)),
        "congestion_risk": (
            "high" if projected >= 8
            else "medium" if projected >= 4
            else "low"
        ),
        "data_ready": bool(events),
        "data_note": (
            "Queue prediction becomes materially stronger once anonymous "
            "queue_join/checkout_complete events are fed by counter sensors."
            if not events else
            "Prediction based on locally recorded anonymous queue events."
        ),
    }


def control_room(conn):
    inv = inventory_intelligence(conn)
    leaks = revenue_leak_radar(conn)
    shopper = shopper_intelligence(conn)
    queue = queue_intelligence(conn)

    risky = [x for x in inv if x["risk"] in ("critical", "high")]
    low_stock = [x for x in inv if x["current_stock"] <= x["minimum_stock"]]

    actions = []
    for p in sorted(risky, key=lambda x: (x["days_to_stockout"] is None, x["days_to_stockout"] or 999))[:5]:
        if p["recommended_order_qty"] > 0:
            actions.append({
                "priority": "high" if p["risk"] == "critical" else "medium",
                "action": "replenish",
                "title": f"Replenish {p['name']}",
                "quantity": p["recommended_order_qty"],
                "reason": p["explanation"],
            })

    if queue["congestion_risk"] == "high":
        actions.append({
            "priority": "high",
            "action": "open_counter",
            "title": "Open an additional checkout counter",
            "reason": f"Predicted 15-minute load: {queue['predicted_load_in_15min']}",
        })

    return {
        "generated_at": _now().isoformat(),
        "kpis": {
            "revenue_exposure": leaks["estimated_exposure"],
            "high_risk_products": len(risky),
            "low_stock_products": len(low_stock),
            "active_guardian_alerts": leaks["active_guardian_alerts"],
            "avg_basket_value": shopper["avg_basket_value"],
            "queue_risk": queue["congestion_risk"],
        },
        "inventory": sorted(
            inv,
            key=lambda x: (
                x["risk"] not in ("critical", "high"),
                x["days_to_stockout"] is None,
                x["days_to_stockout"] or 999,
            ),
        )[:10],
        "revenue_leaks": leaks,
        "shopper": shopper,
        "queue": queue,
        "actions": actions,
    }
