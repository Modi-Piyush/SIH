"""
Database setup and session management supporting Supabase PostgreSQL Cloud Database
and Local SQLite with automatic offline fallback and demo data seeding.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("database")

try:
    from supabase import create_client, Client
    SUPABASE_LIB_AVAILABLE = True
except ImportError:
    SUPABASE_LIB_AVAILABLE = False

def get_supabase_client() -> Optional[Any]:
    """Returns initialized Supabase Client if SUPABASE_URL and SUPABASE_KEY are provided in .env."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or url.startswith("https://your-") or not SUPABASE_LIB_AVAILABLE:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {e}")
        return None

def get_db_engine_status() -> Dict[str, Any]:
    """Returns active database configuration status (Supabase Cloud vs SQLite Local)."""
    supabase_configured = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY") and not os.getenv("SUPABASE_URL", "").startswith("https://your-"))
    database_url_configured = bool(os.getenv("DATABASE_URL"))
    
    return {
        "primary_database": "Supabase Cloud (PostgreSQL)" if (supabase_configured or database_url_configured) else "Local SQLite (Offline-Ready)",
        "supabase_configured": supabase_configured or database_url_configured,
        "sqlite_local_path": get_db_path(),
        "status": "connected"
    }

def get_db_path() -> str:
    """Resolves SQLite database path, automatically using /tmp in serverless/Vercel environments."""
    if os.environ.get("DB_PATH"):
        return os.environ["DB_PATH"]
    
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(os.path.dirname(os.path.abspath(__file__)), os.W_OK))
    if is_serverless:
        tmp_db = "/tmp/procurement.db"
        bundled_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "procurement.db")
        if not os.path.exists(tmp_db) and os.path.exists(bundled_db):
            try:
                import shutil
                shutil.copy2(bundled_db, tmp_db)
            except Exception:
                pass
        return tmp_db
    
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "procurement.db")

def get_db_connection():
    """Returns a SQLite connection configured with row_factory as sqlite3.Row and timeout."""
    db_file = get_db_path()
    conn = sqlite3.connect(db_file, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users / Farmers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        village TEXT NOT NULL,
        district TEXT NOT NULL DEFAULT 'Varanasi',
        land_acres REAL NOT NULL,
        farmer_category TEXT NOT NULL CHECK(farmer_category IN ('SMALL', 'LARGE')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Procurement Centers (PACS) Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS procurement_centers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        district TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        max_capacity_q REAL NOT NULL,
        current_stock_q REAL NOT NULL DEFAULT 0,
        incoming_booked_q REAL NOT NULL DEFAULT 0,
        daily_processing_cap_q REAL NOT NULL DEFAULT 600,
        weighbridge_speed_per_hr REAL NOT NULL DEFAULT 60,
        quality_inspectors_count INTEGER NOT NULL DEFAULT 2,
        status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'MAINTENANCE', 'LOCKED')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Slots / Bookings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_code TEXT UNIQUE NOT NULL,
        farmer_id INTEGER NOT NULL,
        center_id INTEGER NOT NULL,
        crop_category TEXT NOT NULL CHECK(crop_category IN ('Pulses', 'Grains')),
        crop_name TEXT NOT NULL,
        land_acres REAL NOT NULL,
        weight_input_mode TEXT NOT NULL CHECK(weight_input_mode IN ('ESTIMATE', 'EXACT')),
        requested_weight_q REAL NOT NULL,
        allocated_weight_q REAL NOT NULL,
        tranche_number INTEGER NOT NULL DEFAULT 1,
        total_tranches INTEGER NOT NULL DEFAULT 1,
        parent_booking_id INTEGER,
        scheduled_date TEXT NOT NULL,
        arrival_window_start TEXT NOT NULL,
        arrival_window_end TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK(status IN ('CONFIRMED', 'CHECKED_IN', 'QUALITY_APPROVED', 'WEIGHMENT_COMPLETE', 'PAYMENT_DISPATCHED', 'REJECTED', 'REROUTED')),
        tractor_number TEXT,
        qr_payload TEXT,
        rejection_reason TEXT,
        rerouted_from_center_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmer_id) REFERENCES users(id),
        FOREIGN KEY (center_id) REFERENCES procurement_centers(id)
    );
    """)

    # 4. Quality Inspections Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quality_inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_id INTEGER NOT NULL UNIQUE,
        token_code TEXT NOT NULL,
        image_url TEXT,
        moisture_percentage REAL NOT NULL,
        discoloration_percentage REAL NOT NULL,
        foreign_matter_percentage REAL NOT NULL,
        broken_grains_percentage REAL NOT NULL,
        ai_grade TEXT NOT NULL CHECK(ai_grade IN ('A', 'B', 'REJECTED')),
        ai_confidence REAL NOT NULL,
        is_manual_override INTEGER NOT NULL DEFAULT 0,
        override_reason TEXT,
        final_grade TEXT NOT NULL CHECK(final_grade IN ('A', 'B', 'REJECTED')),
        inspector_notes TEXT,
        is_preliminary_assessment INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (slot_id) REFERENCES slots(id)
    );
    """)

    # 5. Weighments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weighments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_id INTEGER NOT NULL UNIQUE,
        token_code TEXT NOT NULL,
        gross_weight_q REAL NOT NULL,
        tare_weight_q REAL NOT NULL,
        net_weight_q REAL NOT NULL,
        estimated_weight_q REAL NOT NULL,
        weight_deviation_percentage REAL NOT NULL,
        is_mismatch_flagged INTEGER NOT NULL DEFAULT 0,
        weighbridge_operator TEXT NOT NULL DEFAULT 'Operator-1',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (slot_id) REFERENCES slots(id)
    );
    """)

    # 6. Procurement Receipts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS procurement_receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_number TEXT UNIQUE NOT NULL,
        slot_id INTEGER NOT NULL UNIQUE,
        token_code TEXT NOT NULL,
        farmer_name TEXT NOT NULL,
        farmer_phone TEXT NOT NULL,
        center_name TEXT NOT NULL,
        crop_name TEXT NOT NULL,
        final_weight_q REAL NOT NULL,
        msp_rate_per_q REAL NOT NULL,
        gross_amount REAL NOT NULL,
        quality_deductions REAL NOT NULL DEFAULT 0,
        net_payable_amount REAL NOT NULL,
        payment_status TEXT NOT NULL DEFAULT 'DISPATCHED' CHECK(payment_status IN ('PENDING', 'DISPATCHED', 'SETTLED')),
        transaction_ref TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (slot_id) REFERENCES slots(id)
    );
    """)

    # 7. Payments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_id INTEGER NOT NULL UNIQUE,
        receipt_id INTEGER,
        farmer_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        msp_rate REAL NOT NULL,
        transaction_ref TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL DEFAULT 'DISPATCHED' CHECK(status IN ('PENDING', 'DISPATCHED', 'SETTLED')),
        disbursed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (slot_id) REFERENCES slots(id),
        FOREIGN KEY (farmer_id) REFERENCES users(id)
    );
    """)

    # 8. Evacuation Alerts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evacuation_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        center_id INTEGER NOT NULL,
        current_fill_percentage REAL NOT NULL,
        trigger_reason TEXT NOT NULL,
        excess_stock_q REAL NOT NULL,
        recommended_trucks INTEGER NOT NULL,
        recommended_destination TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'DISPATCHED', 'RESOLVED')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (center_id) REFERENCES procurement_centers(id)
    );
    """)

    # 9. Offline Transactions Table (for idempotent deduplication sync)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offline_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_tx_id TEXT UNIQUE NOT NULL,
        sync_type TEXT NOT NULL CHECK(sync_type IN ('CHECK_IN', 'WEIGHMENT', 'QUALITY')),
        token_code TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        device_id TEXT NOT NULL DEFAULT 'GATE-TAB-01',
        client_timestamp TEXT NOT NULL,
        synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'SYNCED' CHECK(status IN ('SYNCED', 'DUPLICATE', 'FAILED'))
    );
    """)

    # 10. Notifications Table (SMS simulation)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER NOT NULL,
        phone TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        channel TEXT NOT NULL DEFAULT 'SMS',
        status TEXT NOT NULL DEFAULT 'SENT',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmer_id) REFERENCES users(id)
    );
    """)

    # 11. Center Daily Quotas Table (for 40% smallholder quota tracking)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS center_daily_quotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        center_id INTEGER NOT NULL,
        quota_date TEXT NOT NULL,
        total_daily_cap_q REAL NOT NULL,
        small_farmer_reserved_q REAL NOT NULL,
        small_farmer_booked_q REAL NOT NULL DEFAULT 0,
        general_booked_q REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(center_id, quota_date),
        FOREIGN KEY (center_id) REFERENCES procurement_centers(id)
    );
    """)

    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM procurement_centers")
    centers_count = cursor.fetchone()[0]
    conn.close()
    
    if centers_count == 0:
        seed_demo_data()

def seed_demo_data():
    """Populates initial database state with realistic PACS centers, farmers, and bookings."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data in correct FK order
    cursor.execute("DELETE FROM notifications")
    cursor.execute("DELETE FROM offline_transactions")
    cursor.execute("DELETE FROM evacuation_alerts")
    cursor.execute("DELETE FROM payments")
    cursor.execute("DELETE FROM procurement_receipts")
    cursor.execute("DELETE FROM weighments")
    cursor.execute("DELETE FROM quality_inspections")
    cursor.execute("DELETE FROM slots")
    cursor.execute("DELETE FROM center_daily_quotas")
    cursor.execute("DELETE FROM procurement_centers")
    cursor.execute("DELETE FROM users")
    try:
        cursor.execute("DELETE FROM sqlite_sequence")
    except Exception:
        pass

    # 1. Seed PACS Centers
    centers = [
        ("Rampur PACS Center", "PACS-UP-001", "Varanasi", 25.3176, 82.9739, 2000.0, 750.0, 150.0, 600.0, 60.0, 2, "ACTIVE"),
        ("Bilaspur PACS Center", "PACS-UP-002", "Varanasi", 25.3520, 82.9410, 1500.0, 1140.0, 120.0, 500.0, 50.0, 2, "ACTIVE"),
        ("Sitapur PACS Godown", "PACS-UP-003", "Varanasi", 25.2890, 83.0150, 1000.0, 920.0, 40.0, 400.0, 40.0, 1, "ACTIVE"),
        ("Kalyanpur Buffer Depot", "PACS-UP-004", "Varanasi", 25.3340, 83.0520, 3000.0, 800.0, 200.0, 800.0, 80.0, 3, "ACTIVE")
    ]

    center_ids = {}
    for c in centers:
        cursor.execute("""
        INSERT INTO procurement_centers 
        (name, code, district, lat, lng, max_capacity_q, current_stock_q, incoming_booked_q, daily_processing_cap_q, weighbridge_speed_per_hr, quality_inspectors_count, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, c)
        center_ids[c[1]] = cursor.lastrowid

    # 2. Seed Farmers
    farmers = [
        ("9876543210", "Ramesh Kumar Sharma", "Rampur Kalan", "Varanasi", 3.5, "SMALL"),
        ("9876543211", "Suresh Pratap Singh", "Shivpur Khurd", "Varanasi", 12.0, "LARGE"),
        ("9876543212", "Vikram Patel", "Mirzapur Dehat", "Varanasi", 4.0, "SMALL"),
        ("9876543213", "Anita Devi", "Kashi Gram", "Varanasi", 2.0, "SMALL"),
        ("9876543214", "Rajeshwar Yadav", "Chiraigaon", "Varanasi", 8.5, "LARGE")
    ]

    farmer_ids = {}
    for f in farmers:
        cursor.execute("""
        INSERT INTO users (phone, name, village, district, land_acres, farmer_category)
        VALUES (?, ?, ?, ?, ?, ?)
        """, f)
        farmer_ids[f[0]] = cursor.lastrowid

    today_str = date.today().isoformat()
    rampur_id = center_ids["PACS-UP-001"]
    bilaspur_id = center_ids["PACS-UP-002"]

    # 3. Seed Center Daily Quotas
    for cid in center_ids.values():
        total_daily_cap = 600.0 if cid != center_ids["PACS-UP-004"] else 800.0
        small_reserved = total_daily_cap * 0.40
        cursor.execute("""
        INSERT INTO center_daily_quotas (center_id, quota_date, total_daily_cap_q, small_farmer_reserved_q, small_farmer_booked_q, general_booked_q)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (cid, today_str, total_daily_cap, small_reserved, 120.0, 180.0))

    # 4. Seed Evacuation Alert for Bilaspur
    cursor.execute("""
    INSERT INTO evacuation_alerts (center_id, current_fill_percentage, trigger_reason, excess_stock_q, recommended_trucks, recommended_destination, status)
    VALUES (?, 84.0, 'Storage capacity crossed 80% Warning threshold (Current 84.0%)', 260.0, 3, 'Kalyanpur Buffer Depot (9.4 km)', 'ACTIVE')
    """, (bilaspur_id,))

    # 5. Seed Pre-existing Bookings
    # Slot 1: Confirmed Small Farmer
    f1_id = farmer_ids["9876543210"]
    cursor.execute("""
    INSERT INTO slots (token_code, farmer_id, center_id, crop_category, crop_name, land_acres, weight_input_mode, requested_weight_q, allocated_weight_q, tranche_number, total_tranches, scheduled_date, arrival_window_start, arrival_window_end, status, tractor_number, qr_payload)
    VALUES ('TK-78401', ?, ?, 'Grains', 'Wheat', 3.5, 'ESTIMATE', 50.0, 50.0, 1, 1, ?, '08:00', '10:00', 'CONFIRMED', 'UP-65-AB-1234', '{"token":"TK-78401","farmer":"Ramesh Kumar Sharma","crop":"Wheat","qty":50.0,"center":"Rampur PACS Center"}')
    """, (f1_id, rampur_id, today_str))

    # Slot 2: Checked-in Farmer in Clerk Queue
    f3_id = farmer_ids["9876543212"]
    cursor.execute("""
    INSERT INTO slots (token_code, farmer_id, center_id, crop_category, crop_name, land_acres, weight_input_mode, requested_weight_q, allocated_weight_q, tranche_number, total_tranches, scheduled_date, arrival_window_start, arrival_window_end, status, tractor_number, qr_payload)
    VALUES ('TK-78402', ?, ?, 'Pulses', 'Chana', 4.0, 'ESTIMATE', 32.0, 32.0, 1, 1, ?, '10:00', '12:00', 'CHECKED_IN', 'UP-65-XY-5678', '{"token":"TK-78402","farmer":"Vikram Patel","crop":"Chana","qty":32.0,"center":"Rampur PACS Center"}')
    """, (f3_id, rampur_id, today_str))

    # Slot 3: Completed Procurement with Receipt and Payment
    f4_id = farmer_ids["9876543213"]
    cursor.execute("""
    INSERT INTO slots (token_code, farmer_id, center_id, crop_category, crop_name, land_acres, weight_input_mode, requested_weight_q, allocated_weight_q, tranche_number, total_tranches, scheduled_date, arrival_window_start, arrival_window_end, status, tractor_number, qr_payload)
    VALUES ('TK-78403', ?, ?, 'Grains', 'Wheat', 2.0, 'ESTIMATE', 36.0, 36.0, 1, 1, ?, '08:00', '10:00', 'PAYMENT_DISPATCHED', 'UP-65-CD-9012', '{"token":"TK-78403","farmer":"Anita Devi","crop":"Wheat","qty":36.0,"center":"Rampur PACS Center"}')
    """, (f4_id, rampur_id, today_str))
    slot3_id = cursor.lastrowid

    # Inspection for Slot 3
    cursor.execute("""
    INSERT INTO quality_inspections (slot_id, token_code, moisture_percentage, discoloration_percentage, foreign_matter_percentage, broken_grains_percentage, ai_grade, ai_confidence, final_grade, inspector_notes, is_preliminary_assessment)
    VALUES (?, 'TK-78403', 12.8, 1.2, 0.5, 0.8, 'A', 0.96, 'A', 'Grade A certified. Clean, dry grain meeting standard specifications.', 1)
    """, (slot3_id,))

    # Weighment for Slot 3
    cursor.execute("""
    INSERT INTO weighments (slot_id, token_code, gross_weight_q, tare_weight_q, net_weight_q, estimated_weight_q, weight_deviation_percentage, is_mismatch_flagged, weighbridge_operator)
    VALUES (?, 'TK-78403', 56.0, 20.0, 36.0, 36.0, 0.0, 0, 'Operator-1')
    """, (slot3_id,))

    # Receipt for Slot 3
    cursor.execute("""
    INSERT INTO procurement_receipts (receipt_number, slot_id, token_code, farmer_name, farmer_phone, center_name, crop_name, final_weight_q, msp_rate_per_q, gross_amount, quality_deductions, net_payable_amount, payment_status, transaction_ref)
    VALUES ('REC-89001', ?, 'TK-78403', 'Anita Devi', '9876543213', 'Rampur PACS Center', 'Wheat', 36.0, 2275.0, 81900.0, 0.0, 81900.0, 'DISPATCHED', 'TXN-DBT-20260901-8901')
    """, (slot3_id,))
    receipt3_id = cursor.lastrowid

    # Payment for Slot 3
    cursor.execute("""
    INSERT INTO payments (slot_id, receipt_id, farmer_id, amount, msp_rate, transaction_ref, status)
    VALUES (?, ?, ?, 81900.0, 2275.0, 'TXN-DBT-20260901-8901', 'DISPATCHED')
    """, (slot3_id, receipt3_id, f4_id))

    # Notification
    cursor.execute("""
    INSERT INTO notifications (farmer_id, phone, title, message, channel, status)
    VALUES (?, '9876543213', 'भुगतान प्रेषित / Payment Dispatched', 'प्रिय अनीता देवी, गेहूं 36 क्विंटल की खरीद सफल रही। राशि ₹81,900 सीधे आपके आधार लिंक बैंक खाते में भेज दी गई है। संदर्भ: TXN-DBT-20260901-8901', 'SMS', 'SENT')
    """, (f4_id,))

    conn.commit()
    conn.close()
    print("Database initialized and demo data seeded successfully.")

if __name__ == "__main__":
    init_db()
    seed_demo_data()

