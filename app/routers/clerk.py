"""
PACS Clerk / Quality Inspector Router: Live Queue & Scheduled Pipeline, AI Quality Assessment,
Manual Grade Override, Official Weighbridge Recording, Atomic Acceptance & Fulfillment, and Rejections.
"""

import json
import random
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel, Field

from app.database import get_db_connection
from app.services.procurement_engine import validate_weighment_tolerance, calculate_payment_breakdown
from app.services.quality_engine import analyze_crop_image, get_simulated_sample_inspection
from app.services.storage_engine import calculate_s_fill, generate_evacuation_recommendation

router = APIRouter(prefix="/clerk", tags=["Clerk & Quality"])

class AcceptAndFulfillRequest(BaseModel):
    token_code: str
    gross_weight_q: float
    tare_weight_q: float
    moisture_percentage: float
    discoloration_percentage: float = 1.0
    foreign_matter_percentage: float = 0.5
    broken_grains_percentage: float = 1.0
    ai_grade: str
    ai_confidence: float = 0.95
    is_manual_override: bool = False
    override_reason: Optional[str] = None
    final_grade: str
    inspector_notes: Optional[str] = None
    weighbridge_operator: str = "Clerk-Inspector-01"

class RejectCropRequest(BaseModel):
    token_code: str
    rejection_reason: str
    recommendation: Optional[str] = None
    inspector_notes: Optional[str] = None

@router.get("/queue/{center_id}")
def get_checked_in_queue(center_id: int, filter_status: Optional[str] = Query(None)):
    """
    Retrieves full real-time PACS token pipeline:
    - Scheduled & Confirmed upcoming arrivals (who is coming and when)
    - Gate Checked-In farmers
    - Quality Approved & Weighbridge Complete
    - Dispatched receipts
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if filter_status and filter_status.upper() != "ALL":
        cursor.execute("""
        SELECT s.*, u.name as farmer_name, u.phone as farmer_phone, u.village as farmer_village, u.farmer_category
        FROM slots s
        JOIN users u ON s.farmer_id = u.id
        WHERE s.center_id = ? AND s.status = ?
        ORDER BY s.scheduled_date ASC, s.arrival_window_start ASC, s.id ASC
        """, (center_id, filter_status.upper()))
    else:
        cursor.execute("""
        SELECT s.*, u.name as farmer_name, u.phone as farmer_phone, u.village as farmer_village, u.farmer_category
        FROM slots s
        JOIN users u ON s.farmer_id = u.id
        WHERE s.center_id = ? AND s.status IN ('CONFIRMED', 'CHECKED_IN', 'QUALITY_APPROVED', 'WEIGHMENT_COMPLETE', 'PAYMENT_DISPATCHED', 'REJECTED')
        ORDER BY CASE s.status
            WHEN 'CHECKED_IN' THEN 1
            WHEN 'QUALITY_APPROVED' THEN 2
            WHEN 'CONFIRMED' THEN 3
            WHEN 'WEIGHMENT_COMPLETE' THEN 4
            WHEN 'PAYMENT_DISPATCHED' THEN 5
            ELSE 6
        END, s.scheduled_date ASC, s.arrival_window_start ASC, s.id ASC
        """, (center_id,))
    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]

@router.post("/quality-inspect")
async def inspect_crop_sample(
    token_code: Optional[str] = Form(None),
    crop_name: str = Form("Wheat"),
    sample_type: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    AI Crop Quality Inspection:
    Runs CV analysis on sample image or preset sample type.
    Computes moisture %, discoloration %, foreign matter %, and assigns Grade A / B / REJECTED.
    """
    if file:
        image_bytes = await file.read()
        analysis = analyze_crop_image(image_bytes, crop_name=crop_name)
    elif sample_type:
        analysis = get_simulated_sample_inspection(sample_type=sample_type, crop_name=crop_name)
    else:
        analysis = get_simulated_sample_inspection(sample_type="dry_wheat", crop_name=crop_name)

    if token_code:
        analysis["token_code"] = token_code

    return analysis

@router.post("/validate-weighment")
def validate_weighment_preview(
    allocated_weight_q: float,
    gross_weight_q: float,
    tare_weight_q: float
):
    """Live preview of weighment tolerance calculation."""
    net_weight_q = round(gross_weight_q - tare_weight_q, 2)
    if net_weight_q <= 0:
        raise HTTPException(status_code=400, detail="Net weight must be greater than zero (Gross weight must exceed Tare weight).")
    
    return validate_weighment_tolerance(allocated_weight_q, net_weight_q)

@router.post("/accept-and-fulfill")
def accept_crop_and_fulfill(req: AcceptAndFulfillRequest):
    """
    Primary Atomic Action (PRD FR22):
    Atomically:
    1. Validates token & status.
    2. Computes net weight = gross - tare and checks tolerance.
    3. Finalizes quality record & weighment record.
    4. Increments PACS godown stock and decrements incoming booked stock.
    5. Generates electronic receipt (REC-XXXXX) with MSP payment breakdown.
    6. Advances farmer status to PAYMENT_DISPATCHED.
    7. Dispatches simulated payment & SMS notification.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Fetch Slot & Center
    cursor.execute("""
    SELECT s.*, u.name as farmer_name, u.phone as farmer_phone, u.village as farmer_village,
           c.name as center_name, c.current_stock_q, c.incoming_booked_q, c.max_capacity_q
    FROM slots s
    JOIN users u ON s.farmer_id = u.id
    JOIN procurement_centers c ON s.center_id = c.id
    WHERE s.token_code = ?
    """, (req.token_code.strip(),))
    slot = cursor.fetchone()

    if not slot:
        conn.close()
        raise HTTPException(status_code=404, detail="Token not found.")

    if slot["status"] not in ("CHECKED_IN", "CONFIRMED", "QUALITY_APPROVED"):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Cannot fulfill delivery in current status: '{slot['status']}'.")

    # 2. Weighment calculation & tolerance check
    net_weight_q = round(req.gross_weight_q - req.tare_weight_q, 2)
    if net_weight_q <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Net weight must be greater than 0 (Gross weight must exceed Tare weight).")

    tolerance_info = validate_weighment_tolerance(slot["allocated_weight_q"], net_weight_q)

    # 3. Insert or Update Quality Inspection
    cursor.execute("""
    INSERT INTO quality_inspections (
        slot_id, token_code, moisture_percentage, discoloration_percentage,
        foreign_matter_percentage, broken_grains_percentage, ai_grade, ai_confidence,
        is_manual_override, override_reason, final_grade, inspector_notes, is_preliminary_assessment
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ON CONFLICT(slot_id) DO UPDATE SET
        moisture_percentage = excluded.moisture_percentage,
        discoloration_percentage = excluded.discoloration_percentage,
        foreign_matter_percentage = excluded.foreign_matter_percentage,
        broken_grains_percentage = excluded.broken_grains_percentage,
        ai_grade = excluded.ai_grade,
        ai_confidence = excluded.ai_confidence,
        is_manual_override = excluded.is_manual_override,
        override_reason = excluded.override_reason,
        final_grade = excluded.final_grade,
        inspector_notes = excluded.inspector_notes,
        is_preliminary_assessment = 0
    """, (
        slot["id"], slot["token_code"], req.moisture_percentage, req.discoloration_percentage,
        req.foreign_matter_percentage, req.broken_grains_percentage, req.ai_grade, req.ai_confidence,
        1 if req.is_manual_override else 0, req.override_reason, req.final_grade, req.inspector_notes
    ))

    # 4. Insert or Update Weighment
    cursor.execute("""
    INSERT INTO weighments (
        slot_id, token_code, gross_weight_q, tare_weight_q, net_weight_q,
        estimated_weight_q, weight_deviation_percentage, is_mismatch_flagged, weighbridge_operator
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(slot_id) DO UPDATE SET
        gross_weight_q = excluded.gross_weight_q,
        tare_weight_q = excluded.tare_weight_q,
        net_weight_q = excluded.net_weight_q,
        weight_deviation_percentage = excluded.weight_deviation_percentage,
        is_mismatch_flagged = excluded.is_mismatch_flagged
    """, (
        slot["id"], slot["token_code"], req.gross_weight_q, req.tare_weight_q, net_weight_q,
        slot["allocated_weight_q"], tolerance_info["deviation_percentage"],
        1 if tolerance_info["is_mismatch_flagged"] else 0, req.weighbridge_operator
    ))

    # 5. Calculate Payment Breakdown
    pay_calc = calculate_payment_breakdown(slot["crop_name"], net_weight_q, req.final_grade)
    receipt_no = f"REC-{random.randint(10000, 99999)}"
    txn_ref = f"TXN-DBT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    # 6. Insert Procurement Receipt
    cursor.execute("""
    INSERT INTO procurement_receipts (
        receipt_number, slot_id, token_code, farmer_name, farmer_phone,
        center_name, crop_name, final_weight_q, msp_rate_per_q, gross_amount,
        quality_deductions, net_payable_amount, payment_status, transaction_ref
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISPATCHED', ?)
    ON CONFLICT(slot_id) DO UPDATE SET
        final_weight_q = excluded.final_weight_q,
        gross_amount = excluded.gross_amount,
        quality_deductions = excluded.quality_deductions,
        net_payable_amount = excluded.net_payable_amount,
        payment_status = 'DISPATCHED'
    """, (
        receipt_no, slot["id"], slot["token_code"], slot["farmer_name"], slot["farmer_phone"],
        slot["center_name"], slot["crop_name"], net_weight_q, pay_calc["msp_rate_per_q"],
        pay_calc["gross_amount"], pay_calc["quality_deductions"], pay_calc["net_payable_amount"],
        txn_ref
    ))
    receipt_id = cursor.lastrowid

    # 7. Insert Payment record
    cursor.execute("""
    INSERT INTO payments (slot_id, receipt_id, farmer_id, amount, msp_rate, transaction_ref, status)
    VALUES (?, ?, ?, ?, ?, ?, 'DISPATCHED')
    ON CONFLICT(slot_id) DO UPDATE SET
        amount = excluded.amount,
        status = 'DISPATCHED'
    """, (slot["id"], receipt_id, slot["farmer_id"], pay_calc["net_payable_amount"], pay_calc["msp_rate_per_q"], txn_ref))

    # 8. Update PACS Godown Inventory
    new_stock = slot["current_stock_q"] + net_weight_q
    new_incoming = max(0.0, slot["incoming_booked_q"] - slot["allocated_weight_q"])
    cursor.execute("""
    UPDATE procurement_centers 
    SET current_stock_q = ?, incoming_booked_q = ?
    WHERE id = ?
    """, (new_stock, new_incoming, slot["center_id"]))

    # Check evacuation alert trigger on new stock
    new_s_fill = calculate_s_fill(new_stock, new_incoming, slot["max_capacity_q"])
    if new_s_fill >= 80.0:
        evac = generate_evacuation_recommendation(
            slot["center_id"], slot["center_name"], new_s_fill,
            new_stock, new_incoming, slot["max_capacity_q"]
        )
        if evac:
            cursor.execute("""
            INSERT INTO evacuation_alerts (center_id, current_fill_percentage, trigger_reason, excess_stock_q, recommended_trucks, recommended_destination, status)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (evac["center_id"], evac["current_fill_percentage"], evac["trigger_reason"], evac["excess_stock_q"], evac["recommended_trucks"], evac["recommended_destination"]))

    # 9. Update Slot Status to PAYMENT_DISPATCHED
    cursor.execute("""
    UPDATE slots 
    SET status = 'PAYMENT_DISPATCHED', updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (slot["id"],))

    # 10. Send SMS Notification to Farmer
    sms_msg = (
        f"प्रिय {slot['farmer_name']}, आपकी {slot['crop_name']} ({net_weight_q} Q, ग्रेड {req.final_grade}) खरीद पूर्ण हुई। "
        f"कुल राशि ₹{pay_calc['net_payable_amount']:,} DBT के माध्यम से आपके खाते में प्रेषित कर दी गई है। "
        f"रसीद: {receipt_no}, संदर्भ: {txn_ref}।"
    )
    cursor.execute("""
    INSERT INTO notifications (farmer_id, phone, title, message, channel, status)
    VALUES (?, ?, 'खरीद व भुगतान पुष्टि / Procurement & Payment Complete', ?, 'SMS', 'SENT')
    """, (slot["farmer_id"], slot["farmer_phone"], sms_msg))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "action": "ACCEPT_AND_FULFILL_COMPLETE",
        "token_code": slot["token_code"],
        "receipt_number": receipt_no,
        "transaction_ref": txn_ref,
        "farmer_name": slot["farmer_name"],
        "crop_name": slot["crop_name"],
        "net_weight_q": net_weight_q,
        "quality_grade": req.final_grade,
        "payment_breakdown": pay_calc,
        "pacs_updated_stock_q": new_stock,
        "pacs_storage_fill_pct": new_s_fill,
        "sms_sent": sms_msg
    }

@router.post("/reject")
def reject_crop_delivery(req: RejectCropRequest):
    """
    Reject Delivery Flow (PRD FR23):
    Updates status to REJECTED, records structured reason, and releases incoming storage quota.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.*, u.name as farmer_name, u.phone as farmer_phone,
           c.incoming_booked_q
    FROM slots s
    JOIN users u ON s.farmer_id = u.id
    JOIN procurement_centers c ON s.center_id = c.id
    WHERE s.token_code = ?
    """, (req.token_code.strip(),))
    slot = cursor.fetchone()

    if not slot:
        conn.close()
        raise HTTPException(status_code=404, detail="Token not found.")

    # Update slot to REJECTED
    cursor.execute("""
    UPDATE slots 
    SET status = 'REJECTED', rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (f"{req.rejection_reason} | {req.recommendation or ''}", slot["id"]))

    # Release incoming booked stock
    new_incoming = max(0.0, slot["incoming_booked_q"] - slot["allocated_weight_q"])
    cursor.execute("UPDATE procurement_centers SET incoming_booked_q = ? WHERE id = ?", (new_incoming, slot["center_id"]))

    # Send Notification
    rec_text = req.recommendation or "कृपया फसल को धूप में 2-3 दिन सुखाकर पुन: लाएं।"
    sms_msg = (
        f"सूचना: टोकन {slot['token_code']} अस्वीकृत हुआ। कारण: {req.rejection_reason}। "
        f"परामर्श: {rec_text}।"
    )
    cursor.execute("""
    INSERT INTO notifications (farmer_id, phone, title, message, channel, status)
    VALUES (?, ?, 'फसल अस्वीकृति सूचना / Crop Rejection Notice', ?, 'SMS', 'SENT')
    """, (slot["farmer_id"], slot["farmer_phone"], sms_msg))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "new_status": "REJECTED",
        "token_code": slot["token_code"],
        "reason": req.rejection_reason,
        "recommendation": req.recommendation,
        "message": f"Delivery rejected. Token {slot['token_code']} marked REJECTED and incoming quota released."
    }
