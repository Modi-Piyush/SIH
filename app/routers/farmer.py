"""
Farmer Router: Registration/Login, Crop Yield Calculation, Smart Slot Booking,
Digital Token Issuance, Live Status Tracking, History, Notifications & Pre-Screening.
"""

import json
import re
import random
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field, field_validator

from app.database import get_db_connection
from app.services.procurement_engine import (
    CROP_MULTIPLIERS, CROP_CATEGORIES, CROP_MSP_RATES,
    calculate_crop_weight, is_small_farmer, generate_tranches,
    check_social_equity_quota
)
from app.services.storage_engine import (
    calculate_s_fill, evaluate_storage_state, find_nearest_available_center,
    generate_evacuation_recommendation
)
from app.services.queue_engine import allocate_optimal_arrival_window
from app.services.quality_engine import analyze_crop_image, get_simulated_sample_inspection

router = APIRouter(prefix="/api/farmer", tags=["Farmer"])

INDIAN_MOBILE_REGEX = r"^[6-9]\d{9}$"

class FarmerRegisterRequest(BaseModel):
    phone: str = Field(..., description="10-digit Indian Mobile Number")
    name: str = Field(..., min_length=2)
    village: str = Field(..., min_length=2)
    district: str = Field(default="Varanasi")
    land_acres: float = Field(..., gt=0)

    @field_validator("phone")
    def validate_phone(cls, v):
        clean_phone = v.strip().replace(" ", "").replace("+91", "").replace("-", "")
        if not re.match(INDIAN_MOBILE_REGEX, clean_phone):
            raise ValueError("Mobile number must be a valid 10-digit Indian mobile number starting with 6-9.")
        return clean_phone

class CalculateWeightRequest(BaseModel):
    crop_name: str
    land_acres: float
    mode: str = Field(default="ESTIMATE", description="'ESTIMATE' or 'EXACT'")
    exact_weight_q: Optional[float] = None

class BookSlotRequest(BaseModel):
    farmer_id: Optional[int] = None
    phone: Optional[str] = None
    center_id: int
    crop_name: str
    land_acres: float
    weight_input_mode: str = "ESTIMATE"
    requested_weight_q: Optional[float] = None
    tractor_number: Optional[str] = None
    scheduled_date: Optional[str] = None

@router.post("/register-or-login")
def register_or_login(req: FarmerRegisterRequest):
    """Registers a new farmer or updates existing profile."""
    conn = get_db_connection()
    cursor = conn.cursor()

    category = "SMALL" if is_small_farmer(req.land_acres) else "LARGE"

    cursor.execute("SELECT * FROM users WHERE phone = ?", (req.phone,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
        UPDATE users 
        SET name = ?, village = ?, district = ?, land_acres = ?, farmer_category = ?
        WHERE id = ?
        """, (req.name, req.village, req.district, req.land_acres, category, existing["id"]))
        conn.commit()
        user_id = existing["id"]
        action = "LOGGED_IN"
    else:
        cursor.execute("""
        INSERT INTO users (phone, name, village, district, land_acres, farmer_category)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (req.phone, req.name, req.village, req.district, req.land_acres, category))
        conn.commit()
        user_id = cursor.lastrowid
        action = "REGISTERED"

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = dict(cursor.fetchone())
    conn.close()

    return {
        "status": "success",
        "action": action,
        "farmer": user,
        "is_small_farmer": user["farmer_category"] == "SMALL",
        "equity_message": "Classified as Small Farmer (<=5 acres). Guaranteed 40% center volume reservation applies." if user["farmer_category"] == "SMALL" else "Classified as Large Farmer (>5 acres). General quota and 50Q daily capping rules apply."
    }

@router.get("/profile/{phone}")
def get_farmer_profile(phone: str):
    """Retrieves farmer profile by phone number."""
    clean_phone = phone.strip().replace(" ", "").replace("+91", "").replace("-", "")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (clean_phone,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="Farmer not found. Please register.")
    return dict(user)

@router.post("/calculate-weight")
def calculate_weight(req: CalculateWeightRequest):
    """Calculates crop yield estimate, tranche schedule, and category info."""
    if req.crop_name not in CROP_MULTIPLIERS:
        raise HTTPException(status_code=400, detail=f"Invalid crop. Supported: {list(CROP_MULTIPLIERS.keys())}")

    multiplier = CROP_MULTIPLIERS[req.crop_name]
    category = CROP_CATEGORIES[req.crop_name]
    msp_rate = CROP_MSP_RATES.get(req.crop_name, 2275.0)

    if req.mode == "EXACT" and req.exact_weight_q and req.exact_weight_q > 0:
        total_weight_q = round(req.exact_weight_q, 2)
        estimated_from_land = round(req.land_acres * multiplier, 2)
    else:
        total_weight_q = round(req.land_acres * multiplier, 2)
        estimated_from_land = total_weight_q

    tranches = generate_tranches(total_weight_q)
    is_small = is_small_farmer(req.land_acres)
    gross_msp_value = round(total_weight_q * msp_rate, 2)

    return {
        "crop_name": req.crop_name,
        "crop_category": category,
        "multiplier_q_per_acre": multiplier,
        "land_acres": req.land_acres,
        "total_weight_q": total_weight_q,
        "estimated_weight_q": estimated_from_land,
        "msp_rate_per_q": msp_rate,
        "estimated_gross_payout": gross_msp_value,
        "is_small_farmer": is_small,
        "tranches": tranches,
        "requires_tranching": len(tranches) > 1,
        "tranche_notice": f"Quantity ({total_weight_q} Q) exceeds 50 Q daily limit. Auto-split into {len(tranches)} sequential tranches." if len(tranches) > 1 else "Eligible for single-day booking (<= 50 Q)."
    }

@router.get("/centers")
def list_centers():
    """Lists all PACS centers with live S_fill storage %, Safe/Warning/Critical badges, and nearest reroute if critical."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM procurement_centers ORDER BY id")
    rows = cursor.fetchall()
    all_centers = [dict(r) for r in rows]

    enriched = []
    for c in all_centers:
        s_fill = calculate_s_fill(c["current_stock_q"], c["incoming_booked_q"], c["max_capacity_q"])
        state = evaluate_storage_state(s_fill)
        c_dict = {
            **c,
            "s_fill_percentage": s_fill,
            "storage_state": state,
            "available_capacity_q": max(0.0, round(c["max_capacity_q"] - (c["current_stock_q"] + c["incoming_booked_q"]), 2)),
            "is_locked": state == "Critical",
            "reroute_recommendation": None
        }

        if state == "Critical":
            reroute = find_nearest_available_center(c, all_centers)
            c_dict["reroute_recommendation"] = reroute

        enriched.append(c_dict)

    conn.close()
    return enriched

@router.post("/book-slot")
def book_slot(req: BookSlotRequest):
    """
    Core Smart Booking Endpoint:
    1. Validates Farmer & Crop.
    2. Computes Weight & Multipliers.
    3. Storage-Aware Admission Control:
       - Recomputes S_fill at commit-time.
       - If Critical (>=95%), blocks and returns 15km nearest center reroute suggestion.
       - If Warning (80-95%), allows booking + creates background evacuation alert.
    4. Backend Social Equity Engine:
       - Enforces 40% Small Farmer volume reservation.
       - Enforces 50Q daily cap (auto-tranching).
    5. Dynamic Arrival Window:
       - Assigns 2-hour arrival window.
    6. Issues Digital Token (TK-XXXXX) + QR payload + SMS notification.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Resolve Farmer
    if req.farmer_id:
        cursor.execute("SELECT * FROM users WHERE id = ?", (req.farmer_id,))
        farmer = cursor.fetchone()
    elif req.phone:
        clean_phone = req.phone.strip().replace(" ", "").replace("+91", "").replace("-", "")
        cursor.execute("SELECT * FROM users WHERE phone = ?", (clean_phone,))
        farmer = cursor.fetchone()
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Farmer ID or Phone is required.")

    if not farmer:
        conn.close()
        raise HTTPException(status_code=404, detail="Farmer not found. Please register first.")

    farmer_id = farmer["id"]
    land_acres = req.land_acres or farmer["land_acres"]
    is_small = is_small_farmer(land_acres)

    # 2. Check Crop
    if req.crop_name not in CROP_MULTIPLIERS:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Unsupported crop: {req.crop_name}")

    multiplier = CROP_MULTIPLIERS[req.crop_name]
    crop_category = CROP_CATEGORIES[req.crop_name]

    if req.weight_input_mode == "EXACT" and req.requested_weight_q and req.requested_weight_q > 0:
        total_weight_q = round(req.requested_weight_q, 2)
    else:
        total_weight_q = round(land_acres * multiplier, 2)

    # 3. Check Center & Real-Time Storage
    cursor.execute("SELECT * FROM procurement_centers WHERE id = ?", (req.center_id,))
    center = cursor.fetchone()
    if not center:
        conn.close()
        raise HTTPException(status_code=404, detail="Procurement Center not found.")

    center_dict = dict(center)
    s_fill = calculate_s_fill(center_dict["current_stock_q"], center_dict["incoming_booked_q"], center_dict["max_capacity_q"])
    storage_state = evaluate_storage_state(s_fill)

    # CRITICAL LOCK CHECK (PRD Section 6.3)
    if storage_state == "Critical":
        # Fetch all centers for rerouting search
        cursor.execute("SELECT * FROM procurement_centers")
        all_centers = [dict(r) for r in cursor.fetchall()]
        reroute = find_nearest_available_center(center_dict, all_centers, requested_weight_q=total_weight_q)
        conn.close()
        
        detail_msg = f"Booking locked: {center_dict['name']} has reached Critical storage capacity ({s_fill}% full)."
        if reroute:
            detail_msg += f" Nearest available center is {reroute['name']} ({reroute['distance_km']} km away, {reroute['s_fill']}% used)."
        
        raise HTTPException(
            status_code=423, # Locked
            detail={
                "error": "STORAGE_CRITICAL_LOCKED",
                "message": detail_msg,
                "current_center": center_dict["name"],
                "s_fill": s_fill,
                "reroute_recommendation": reroute
            }
        )

    # 4. Auto-Tranching (PRD Section 6.2)
    booking_date = req.scheduled_date or date.today().isoformat()
    tranches = generate_tranches(total_weight_q)

    # 5. Check Social Equity Quotas for Tranche 1
    cursor.execute("SELECT * FROM center_daily_quotas WHERE center_id = ? AND quota_date = ?", (req.center_id, booking_date))
    daily_quota = cursor.fetchone()
    daily_cap = center_dict.get("daily_processing_cap_q", 600.0)
    small_booked = daily_quota["small_farmer_booked_q"] if daily_quota else 0.0
    general_booked = daily_quota["general_booked_q"] if daily_quota else 0.0

    tranche_1_weight = tranches[0]["allocated_weight_q"]
    allowed, equity_msg = check_social_equity_quota(
        land_acres, tranche_1_weight, daily_cap, small_booked, general_booked
    )

    if not allowed:
        conn.close()
        raise HTTPException(status_code=400, detail={"error": "EQUITY_QUOTA_EXHAUSTED", "message": equity_msg})

    # 6. Fetch Existing Bookings for Queue Window Allocation
    cursor.execute("""
    SELECT arrival_window_start, arrival_window_end, allocated_weight_q 
    FROM slots 
    WHERE center_id = ? AND scheduled_date = ? AND status NOT IN ('REJECTED', 'REROUTED')
    """, (req.center_id, booking_date))
    existing_slots = [dict(r) for r in cursor.fetchall()]
    
    by_window: Dict[str, List[Dict[str, Any]]] = {}
    for s in existing_slots:
        w_key = f"{s['arrival_window_start']}-{s['arrival_window_end']}"
        by_window.setdefault(w_key, []).append(s)

    window_alloc = allocate_optimal_arrival_window(
        by_window, tranche_1_weight, is_small,
        weighbridge_speed_per_hr=center_dict.get("weighbridge_speed_per_hr", 60.0)
    )

    # 7. Create Bookings (Parent + child tranches if > 50Q)
    created_tokens = []
    parent_slot_id = None

    for i, tranche in enumerate(tranches):
        token_num = random.randint(10000, 99999)
        token_code = f"TK-{token_num}"
        
        # QR payload
        qr_data = {
            "token": token_code,
            "farmer": farmer["name"],
            "phone": farmer["phone"],
            "crop": req.crop_name,
            "qty_q": tranche["allocated_weight_q"],
            "tranche": f"{tranche['tranche_number']}/{tranche['total_tranches']}",
            "center": center_dict["name"],
            "date": tranche["scheduled_date"],
            "window": f"{window_alloc['arrival_window_start']} - {window_alloc['arrival_window_end']}"
        }

        tractor_no = req.tractor_number or f"UP-65-{random.choice(['AB','CD','EF','GH'])}-{random.randint(1000,9999)}"

        cursor.execute("""
        INSERT INTO slots (
            token_code, farmer_id, center_id, crop_category, crop_name, land_acres,
            weight_input_mode, requested_weight_q, allocated_weight_q, tranche_number,
            total_tranches, parent_booking_id, scheduled_date, arrival_window_start,
            arrival_window_end, status, tractor_number, qr_payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?, ?)
        """, (
            token_code, farmer_id, req.center_id, crop_category, req.crop_name, land_acres,
            req.weight_input_mode, total_weight_q, tranche["allocated_weight_q"],
            tranche["tranche_number"], tranche["total_tranches"], parent_slot_id,
            tranche["scheduled_date"], window_alloc["arrival_window_start"],
            window_alloc["arrival_window_end"], tractor_no, json.dumps(qr_data)
        ))

        slot_id = cursor.lastrowid
        if i == 0:
            parent_slot_id = slot_id

        created_tokens.append({
            "token_code": token_code,
            "slot_id": slot_id,
            "tranche_number": tranche["tranche_number"],
            "total_tranches": tranche["total_tranches"],
            "allocated_weight_q": tranche["allocated_weight_q"],
            "scheduled_date": tranche["scheduled_date"],
            "arrival_window": f"{window_alloc['arrival_window_start']} - {window_alloc['arrival_window_end']}",
            "tractor_number": tractor_no,
            "qr_payload": qr_data
        })

    # 8. Update Center Incoming Stock
    new_incoming = center_dict["incoming_booked_q"] + total_weight_q
    cursor.execute("UPDATE procurement_centers SET incoming_booked_q = ? WHERE id = ?", (new_incoming, req.center_id))

    # 9. Update Center Daily Quotas
    if is_small:
        cursor.execute("""
        INSERT INTO center_daily_quotas (center_id, quota_date, total_daily_cap_q, small_farmer_reserved_q, small_farmer_booked_q, general_booked_q)
        VALUES (?, ?, ?, ?, ?, 0)
        ON CONFLICT(center_id, quota_date) DO UPDATE SET small_farmer_booked_q = small_farmer_booked_q + ?
        """, (req.center_id, booking_date, daily_cap, daily_cap * 0.40, tranche_1_weight, tranche_1_weight))
    else:
        cursor.execute("""
        INSERT INTO center_daily_quotas (center_id, quota_date, total_daily_cap_q, small_farmer_reserved_q, small_farmer_booked_q, general_booked_q)
        VALUES (?, ?, ?, ?, 0, ?)
        ON CONFLICT(center_id, quota_date) DO UPDATE SET general_booked_q = general_booked_q + ?
        """, (req.center_id, booking_date, daily_cap, daily_cap * 0.40, tranche_1_weight, tranche_1_weight))

    # 10. Check if Warning Evacuation Alert is needed (PRD Section 6.3)
    new_s_fill = calculate_s_fill(center_dict["current_stock_q"], new_incoming, center_dict["max_capacity_q"])
    if new_s_fill >= 80.0:
        evac = generate_evacuation_recommendation(
            center_dict["id"], center_dict["name"], new_s_fill,
            center_dict["current_stock_q"], new_incoming, center_dict["max_capacity_q"]
        )
        if evac:
            cursor.execute("""
            INSERT INTO evacuation_alerts (center_id, current_fill_percentage, trigger_reason, excess_stock_q, recommended_trucks, recommended_destination, status)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (evac["center_id"], evac["current_fill_percentage"], evac["trigger_reason"], evac["excess_stock_q"], evac["recommended_trucks"], evac["recommended_destination"]))

    # 11. Send Simulated SMS Notification
    primary_token = created_tokens[0]
    sms_text = (
        f"प्रिय {farmer['name']}, ई-खरीद टोकन {primary_token['token_code']} स्वीकृत हुआ। "
        f"फसल: {req.crop_name} ({primary_token['allocated_weight_q']} Q)। "
        f"केंद्र: {center_dict['name']}। तारीख: {primary_token['scheduled_date']}, समय: {primary_token['arrival_window']}।"
    )
    cursor.execute("""
    INSERT INTO notifications (farmer_id, phone, title, message, channel, status)
    VALUES (?, ?, 'टोकन बुकिंग पुष्टि / Token Confirmed', ?, 'SMS', 'SENT')
    """, (farmer_id, farmer["phone"], sms_text))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "primary_token": primary_token["token_code"],
        "tokens": created_tokens,
        "farmer_name": farmer["name"],
        "farmer_category": farmer["farmer_category"],
        "center_name": center_dict["name"],
        "total_weight_q": total_weight_q,
        "tranches_count": len(created_tokens),
        "sms_sent": sms_text,
        "queue_info": {
            "window": primary_token["arrival_window"],
            "estimated_wait_minutes": window_alloc["estimated_wait_minutes"],
            "queue_depth": window_alloc["estimated_queue_depth"]
        }
    }

@router.get("/tokens/{token_code}")
def get_token_details(token_code: str):
    """Retrieves complete booking details and live status for a token."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.*, u.name as farmer_name, u.phone as farmer_phone, u.village as farmer_village, u.farmer_category,
           c.name as center_name, c.district as center_district, c.lat as center_lat, c.lng as center_lng
    FROM slots s
    JOIN users u ON s.farmer_id = u.id
    JOIN procurement_centers c ON s.center_id = c.id
    WHERE s.token_code = ?
    """, (token_code,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Token not found.")

    slot_data = dict(row)

    # Fetch quality inspection if present
    cursor.execute("SELECT * FROM quality_inspections WHERE slot_id = ?", (slot_data["id"],))
    qi = cursor.fetchone()
    slot_data["quality_inspection"] = dict(qi) if qi else None

    # Fetch weighment if present
    cursor.execute("SELECT * FROM weighments WHERE slot_id = ?", (slot_data["id"],))
    w = cursor.fetchone()
    slot_data["weighment"] = dict(w) if w else None

    # Fetch receipt if present
    cursor.execute("SELECT * FROM procurement_receipts WHERE slot_id = ?", (slot_data["id"],))
    rec = cursor.fetchone()
    slot_data["receipt"] = dict(rec) if rec else None

    # Fetch payment if present
    cursor.execute("SELECT * FROM payments WHERE slot_id = ?", (slot_data["id"],))
    pay = cursor.fetchone()
    slot_data["payment"] = dict(pay) if pay else None

    conn.close()
    return slot_data

@router.get("/history/{phone}")
def get_farmer_history(phone: str):
    """Retrieves all past and current bookings and receipts for a farmer."""
    clean_phone = phone.strip().replace(" ", "").replace("+91", "").replace("-", "")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, village, land_acres, farmer_category FROM users WHERE phone = ?", (clean_phone,))
    farmer = cursor.fetchone()
    if not farmer:
        conn.close()
        return {"farmer": None, "slots": [], "receipts": []}

    cursor.execute("""
    SELECT s.*, c.name as center_name 
    FROM slots s
    JOIN procurement_centers c ON s.center_id = c.id
    WHERE s.farmer_id = ?
    ORDER BY s.id DESC
    """, (farmer["id"],))
    slots = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
    SELECT r.* 
    FROM procurement_receipts r
    JOIN slots s ON r.slot_id = s.id
    WHERE s.farmer_id = ?
    ORDER BY r.id DESC
    """, (farmer["id"],))
    receipts = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "farmer": dict(farmer),
        "slots": slots,
        "receipts": receipts
    }

@router.get("/notifications/{phone}")
def get_farmer_notifications(phone: str):
    """Retrieves simulated SMS messages for a farmer."""
    clean_phone = phone.strip().replace(" ", "").replace("+91", "").replace("-", "")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM notifications 
    WHERE phone = ? 
    ORDER BY id DESC LIMIT 20
    """, (clean_phone,))
    notes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return notes

@router.post("/pre-screening")
async def pre_screen_crop(
    crop_name: str = Form("Wheat"),
    sample_type: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Farmer AI Crop Quality / Moisture Pre-Screening:
    Provides pre-trip moisture & discoloration analysis so farmer does not waste a trip to the Mandi.
    """
    if file:
        image_bytes = await file.read()
        result = analyze_crop_image(image_bytes, crop_name=crop_name)
    elif sample_type:
        result = get_simulated_sample_inspection(sample_type=sample_type, crop_name=crop_name)
    else:
        result = get_simulated_sample_inspection(sample_type="dry_wheat", crop_name=crop_name)

    return result
