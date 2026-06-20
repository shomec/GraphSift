import random
import uuid
from datetime import datetime

# Define standard clean endpoint schema patterns
def gen_user_profile():
    return {
        "id": random.randint(1000, 99999),
        "username": f"user_{random.randint(100, 999)}",
        "email": f"user_{random.randint(100, 999)}@example.com",
        "profile": {
            "bio": "Software developer and open source enthusiast.",
            "avatar_url": f"https://assets.example.com/avatars/{uuid.uuid4().hex[:8]}.png",
            "theme": random.choice(["light", "dark", "system"]),
            "age": random.randint(18, 70)
        },
        "roles": random.choices(["user", "admin", "moderator", "billing"], k=random.randint(1, 3)),
        "active": random.choice([True, False]),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

def gen_payment_charge():
    return {
        "transaction_id": f"tx_{uuid.uuid4().hex[:12]}",
        "amount": round(random.uniform(5.0, 1500.0), 2),
        "currency": random.choice(["USD", "EUR", "GBP", "CAD"]),
        "payment_method": {
            "type": random.choice(["credit_card", "paypal", "apple_pay", "bank_transfer"]),
            "card_last4": f"{random.randint(1000, 9999)}",
            "expiry": f"{random.randint(1, 12):02d}/{random.randint(26, 32)}"
        },
        "metadata": {
            "order_id": f"ord_{random.randint(100000, 999999)}",
            "ip_address": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
        },
        "status": random.choice(["pending", "completed", "failed"])
    }

def gen_inventory_item():
    return {
        "item_code": f"SKU-{random.randint(1000, 9999)}-{random.choice(['A', 'B', 'C'])}",
        "quantity": random.randint(0, 500),
        "warehouse": f"WH-{random.choice(['East', 'West', 'Central'])}",
        "details": {
            "dimensions": [round(random.uniform(1.0, 50.0), 1) for _ in range(3)],
            "weight": round(random.uniform(0.1, 75.0), 2),
            "fragile": random.choice([True, False])
        },
        "restock_needed": random.choice([True, False])
    }

# Noise Payloads
def gen_noise_crawler():
    # Simulated search engine scraper or basic probe payload
    return {
        "headers": {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Accept": "*/*"
        },
        "method": "GET",
        "path": random.choice(["/robots.txt", "/sitemap.xml", "/.env", "/wp-login.php"])
    }

def gen_noise_error():
    # Database connection or code crash stack traces
    return {
        "error": "Internal Server Error",
        "code": 500,
        "message": "database connection pool exhausted",
        "timestamp": datetime.utcnow().isoformat(),
        "traceback": "Traceback (most recent call): File '/app/db.py', line 45, in connect ... ConnectionRefusedError"
    }

def gen_noise_ping():
    # Very short heartbeat/ping
    return {"ping": True}

# Anomalous/Drift Payloads
def gen_anomaly_bloat(endpoint_type):
    # Generates a bloated schema with 30-50 extra randomized keys
    if endpoint_type == "user":
        base = gen_user_profile()
    elif endpoint_type == "payment":
        base = gen_payment_charge()
    else:
        base = gen_inventory_item()
        
    for i in range(random.randint(20, 40)):
        base[f"bloat_key_{i}"] = random.choice([
            random.randint(1, 100),
            f"bloat_val_{random.randint(1, 1000)}",
            random.choice([True, False]),
            None
        ])
    return base

def gen_anomaly_type_drift(endpoint_type):
    # Drifts data types (e.g. array becomes string, object becomes flat list)
    if endpoint_type == "user":
        base = gen_user_profile()
        base["roles"] = "user_role_string_instead_of_array"  # type mismatch
        base["profile"] = "bio: dev, age: 25"  # object flattened to string
    elif endpoint_type == "payment":
        base = gen_payment_charge()
        base["amount"] = "one hundred dollars"  # numeric becomes string
        base["payment_method"] = ["credit_card", "1234", "12/28"]  # dict becomes list
    else:
        base = gen_inventory_item()
        base["quantity"] = "out_of_stock"  # int becomes string
        base["details"] = True  # dict becomes boolean
    return base

def gen_anomaly_deep_nesting():
    # Deeply nested object to check nesting depth features (DOS style payload)
    payload = {}
    curr = payload
    for i in range(15):
        curr["nested_step"] = {}
        curr = curr["nested_step"]
    curr["endpoint_flag"] = "deep_nest"
    return payload

def gen_anomaly_large_strings():
    # Long text payload representing potential exploit buffer overflow or large file body
    return {
        "session_id": uuid.uuid4().hex,
        "input_data": "A" * random.randint(8000, 15000),
        "comment": "B" * random.randint(5000, 8000)
    }

def generate_dataset(n_clean=100, n_noise=0):
    """
    Generates a dataset of API payloads containing a mix of endpoints and optional noise.
    """
    dataset = []
    
    # 1. Add clean microservice endpoints
    endpoints = ["user", "payment", "inventory"]
    for _ in range(n_clean):
        ep = random.choice(endpoints)
        if ep == "user":
            payload = gen_user_profile()
        elif ep == "payment":
            payload = gen_payment_charge()
        else:
            payload = gen_inventory_item()
        dataset.append({"endpoint": ep, "payload": payload, "label": "clean"})
        
    # 2. Add noise payloads if requested
    for _ in range(n_noise):
        noise_type = random.choice(["crawler", "error", "ping"])
        if noise_type == "crawler":
            payload = gen_noise_crawler()
        elif noise_type == "error":
            payload = gen_noise_error()
        else:
            payload = gen_noise_ping()
        dataset.append({"endpoint": "noise", "payload": payload, "label": "noise"})
        
    random.shuffle(dataset)
    return dataset

def generate_anomalies():
    """
    Generates a list of all target anomaly types for testing validation.
    """
    anomalies = [
        {"type": "bloat_user", "payload": gen_anomaly_bloat("user"), "endpoint": "user"},
        {"type": "bloat_payment", "payload": gen_anomaly_bloat("payment"), "endpoint": "payment"},
        {"type": "type_drift_user", "payload": gen_anomaly_type_drift("user"), "endpoint": "user"},
        {"type": "type_drift_payment", "payload": gen_anomaly_type_drift("payment"), "endpoint": "payment"},
        {"type": "deep_nesting", "payload": gen_anomaly_deep_nesting(), "endpoint": "unknown"},
        {"type": "large_strings", "payload": gen_anomaly_large_strings(), "endpoint": "unknown"}
    ]
    return anomalies
