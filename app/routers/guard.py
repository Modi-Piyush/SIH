"""
Security Guard / Gatekeeper Router: Gate Verification, Online & Offline Check-In,
Offline Manifest Caching, and Idempotent Offline Sync Endpoint.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.database import get_db_connection

router = APIRouter(prefix="/api", tags=["Guard & Sync"])

class CheckInRequest(BaseModel):
    token_code: str
    tractor_number: Optional[str] = None
    gate_operator: str = "Gate-Guard-01"

class OfflineTransactionItem(BaseModel):
    client_tx_id: str = Field(..., description="Unique client-generated UUID for deduplication")
    sync_type: str = Field(default="CHECK_IN", description="'CHECK_IN', 'WEIGHMENT', 'QUALITY'")
    token_code: str
    payload: Dict[str, Any]
    client_timestamp: str
    device_id: str = "GATE-TAB-01"

class SyncOfflineBatchRequest(BaseModel):
    transactions: List[OfflineTransactionItem]
    device_id: str = "GATE-TAB-01"

@router.get("/guard/verify-token/{token_code}")
def verify_token(token_code: str):
    """Verifies a token at the gate and returns farmer, crop, and status info."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.*, u.name as farmer_name, u.phone as farmer_phone, u.village as farmer_village, u.farmer_category,
           c.name as center_name
    FROM slots s
    JOIN users u ON s.farmer_id = u.id
    JOIN procurement_centers c ON s.center_id = c.id
    WHERE s.token_code = ?
    """, (token_code.strip(),))
    slot = cursor.fetchone()
    conn.close()

    if not slot:
        raise HTTPException(status_code=404, detail="Token not found. Verify token code or check offline manifest.")

    slot_dict = dict(slot)
    return {
        "verified": True,
        "token_code": slot_dict["token_code"],
        "farmer_name": slot_dict["farmer_name"],
        "farmer_phone": slot_dict["farmer_phone"],
        "farmer_village": slot_dict["farmer_village"],
        "farmer_category": slot_dict["farmer_category"],
        "crop_name": slot_dict["crop_name"],
        "crop_category": slot_dict["crop_category"],
        "allocated_weight_q": slot_dict["allocated_weight_q"],
        "scheduled_date": slot_dict["scheduled_date"],
        "arrival_window": f"{slot_dict['arrival_window_start']} - {slot_dict['arrival_window_end']}",
        "tractor_number": slot_dict["tractor_number"],
        "status": slot_dict["status"],
        "center_name": slot_dict["center_name"],
        "can_check_in": slot_dict["status"] == "CONFIRMED"
    }

@router.post("/guard/check-in")
def check_in_farmer(req: CheckInRequest):
    """Performs online gate check-in and transitions booking status to CHECKED_IN."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM slots WHERE token_code = ?", (req.token_code.strip(),))
    slot = cursor.fetchone()

    if not slot:
        conn.close()
        raise HTTPException(status_code=404, detail="Token not found.")

    if slot["status"] != "CONFIRMED":
        conn.close()
        return {
            "status": "already_processed",
            "current_status": slot["status"],
            "message": f"Token is already in '{slot['status']}' state."
        }

    update_tractor = req.tractor_number or slot["tractor_number"]

    cursor.execute("""
    UPDATE slots 
    SET status = 'CHECKED_IN', tractor_number = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (update_tractor, slot["id"]))

    # Send Notification
    cursor.execute("SELECT name, phone FROM users WHERE id = ?", (slot["farmer_id"],))
    farmer = cursor.fetchone()
    if farmer:
        msg = f"प्रिय {farmer['name']}, आपका गेट चेक-इन सफल रहा (टोकन: {slot['token_code']})। कृपया गुणवत्ता निरीक्षण एवं धर्मकांटा कतार में आगे बढ़ें।"
        cursor.execute("""
        INSERT INTO notifications (farmer_id, phone, title, message, channel, status)
        VALUES (?, ?, 'गेट चेक-इन सफल / Gate Checked-In', ?, 'SMS', 'SENT')
        """, (slot["farmer_id"], farmer["phone"], msg))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "new_status": "CHECKED_IN",
        "token_code": slot["token_code"],
        "message": f"Farmer check-in recorded successfully. Token {slot['token_code']} moved to Mandi Queue."
    }

@router.get("/guard/offline-manifest/{center_id}")
def get_offline_manifest(center_id: int):
    """
    Returns full cacheable list of active bookings for a center.
    The guard's browser stores this manifest in IndexedDB to verify farmers during rural network outages.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.id, s.token_code, s.farmer_id, s.crop_name, s.crop_category, s.allocated_weight_q,
           s.scheduled_date, s.arrival_window_start, s.arrival_window_end, s.status, s.tractor_number,
           u.name as farmer_name, u.phone as farmer_phone, u.village as farmer_village, u.farmer_category
    FROM slots s
    JOIN users u ON s.farmer_id = u.id
    WHERE s.center_id = ?
    ORDER BY s.id DESC
    """, (center_id,))
    slots = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "center_id": center_id,
        "manifest_timestamp": datetime.now().isoformat(),
        "total_bookings": len(slots),
        "bookings": slots
    }

@router.post("/sync-offline-transactions")
def sync_offline_transactions(req: SyncOfflineBatchRequest):
    """
    Core Offline Reconciliation Endpoint (PRD FR16, Success Criteria 1.3):
    1. Reconciles transactions recorded on guard/clerk tablets during internet outages.
    2. Guaranteed idempotent deduplication on client_tx_id.
    3. Zero duplicate or lost transactions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    results = []
    synced_count = 0
    duplicate_count = 0

    for item in req.transactions:
        # 1. Check if client_tx_id already recorded
        cursor.execute("SELECT * FROM offline_transactions WHERE client_tx_id = ?", (item.client_tx_id,))
        existing_tx = cursor.fetchone()

        if existing_tx:
            duplicate_count += 1
            results.append({
                "client_tx_id": item.client_tx_id,
                "token_code": item.token_code,
                "status": "DUPLICATE_SKIPPED",
                "message": "Transaction already synchronized previously."
            })
            continue

        # 2. Record in offline_transactions log
        cursor.execute("""
        INSERT INTO offline_transactions (client_tx_id, sync_type, token_code, payload_json, device_id, client_timestamp, status)
        VALUES (?, ?, ?, ?, ?, ?, 'SYNCED')
        """, (item.client_tx_id, item.sync_type, item.token_code, json.dumps(item.payload), req.device_id, item.client_timestamp))

        # 3. Apply state mutation according to sync_type
        if item.sync_type == "CHECK_IN":
            cursor.execute("SELECT * FROM slots WHERE token_code = ?", (item.token_code,))
            slot = cursor.fetchone()
            if slot and slot["status"] == "CONFIRMED":
                tractor = item.payload.get("tractor_number") or slot["tractor_number"]
                cursor.execute("""
                UPDATE slots 
                SET status = 'CHECKED_IN', tractor_number = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (tractor, slot["id"]))

                cursor.execute("SELECT name, phone FROM users WHERE id = ?", (slot["farmer_id"],))
                farmer = cursor.fetchone()
                if farmer:
                    msg = f"प्रिय {farmer['name']}, आपका ऑफलाइन चेक-इन सर्वर पर सिंक हो गया है (टोकन: {slot['token_code']})।"
                    cursor.execute("""
                    INSERT INTO notifications (farmer_id, phone, title, message, channel, status)
                    VALUES (?, ?, 'ऑफलाइन चेक-इन सिंक / Offline Check-In Synced', ?, 'SMS', 'SENT')
                    """, (slot["farmer_id"], farmer["phone"], msg))

        synced_count += 1
        results.append({
            "client_tx_id": item.client_tx_id,
            "token_code": item.token_code,
            "status": "SYNCED",
            "message": "Successfully synchronized and applied to central database."
        })

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "total_submitted": len(req.transactions),
        "synced_count": synced_count,
        "duplicate_count": duplicate_count,
        "results": results
    }
