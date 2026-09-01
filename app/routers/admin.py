"""
District Admin / DOCA Router: Real-time Procurement KPIs, PACS Storage Cards,
Evacuation Alerts Management, System Intelligence Hub, and Demo Data Reset.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db_connection, seed_demo_data
from app.services.storage_engine import calculate_s_fill, evaluate_storage_state, find_nearest_available_center

router = APIRouter(prefix="/api/admin", tags=["District Admin & Command Center"])

class DispatchEvacuationRequest(BaseModel):
    trucks_dispatched: int = 3
    driver_notes: Optional[str] = "Dispatched via State Logistics Fleet"

@router.get("/metrics")
def get_admin_metrics():
    """
    Returns real-time district-level counters:
    Total farmers, today's bookings, checked-in, completed, pending, rejected,
    total quantity procured (Q), and total MSP funds disbursed.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total Farmers
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN farmer_category = 'SMALL' THEN 1 ELSE 0 END) as small_count FROM users")
    farmer_row = cursor.fetchone()
    total_farmers = farmer_row["total"] if farmer_row else 0
    small_farmers = farmer_row["small_count"] if farmer_row else 0

    # Bookings Breakdown
    cursor.execute("""
    SELECT 
        COUNT(*) as total_bookings,
        SUM(CASE WHEN status = 'CONFIRMED' THEN 1 ELSE 0 END) as pending_arrival,
        SUM(CASE WHEN status = 'CHECKED_IN' THEN 1 ELSE 0 END) as checked_in,
        SUM(CASE WHEN status IN ('QUALITY_APPROVED', 'WEIGHMENT_COMPLETE') THEN 1 ELSE 0 END) as in_processing,
        SUM(CASE WHEN status = 'PAYMENT_DISPATCHED' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected
    FROM slots
    """)
    booking_counts = dict(cursor.fetchone())

    # Total Quantity Procured & Total Payout
    cursor.execute("SELECT SUM(final_weight_q) as total_q, SUM(net_payable_amount) as total_payout FROM procurement_receipts")
    receipt_row = cursor.fetchone()
    total_procured_q = receipt_row["total_q"] or 0.0
    total_payout_amount = receipt_row["total_payout"] or 0.0

    # Active Evacuation Alerts
    cursor.execute("SELECT COUNT(*) as active_alerts FROM evacuation_alerts WHERE status = 'ACTIVE'")
    alerts_count = cursor.fetchone()["active_alerts"]

    conn.close()

    return {
        "total_farmers": total_farmers,
        "small_farmers_count": small_farmers,
        "large_farmers_count": total_farmers - small_farmers,
        "small_farmer_percentage": round((small_farmers / max(1, total_farmers)) * 100.0, 1),
        "total_bookings": booking_counts["total_bookings"] or 0,
        "pending_arrival": booking_counts["pending_arrival"] or 0,
        "checked_in": booking_counts["checked_in"] or 0,
        "in_processing": booking_counts["in_processing"] or 0,
        "completed": booking_counts["completed"] or 0,
        "rejected": booking_counts["rejected"] or 0,
        "total_procured_q": round(total_procured_q, 1),
        "total_payout_inr": round(total_payout_amount, 2),
        "total_payout_crores": round(total_payout_amount / 10000000.0, 4),
        "active_evacuation_alerts": alerts_count
    }

@router.get("/centers")
def get_pacs_centers():
    """Returns all PACS centers with real-time storage metrics, thresholds, and reroute suggestions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM procurement_centers ORDER BY id ASC")
    rows = cursor.fetchall()
    all_centers = [dict(r) for r in rows]

    enriched = []
    for c in all_centers:
        s_fill = calculate_s_fill(c["current_stock_q"], c["incoming_booked_q"], c["max_capacity_q"])
        state = evaluate_storage_state(s_fill)
        
        # Count checked-in and completed slots for this center
        cursor.execute("SELECT COUNT(*) as cnt FROM slots WHERE center_id = ? AND status = 'CHECKED_IN'", (c["id"],))
        live_queue = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM slots WHERE center_id = ? AND status = 'PAYMENT_DISPATCHED'", (c["id"],))
        procured_today = cursor.fetchone()["cnt"]

        c_info = {
            **c,
            "s_fill_percentage": s_fill,
            "storage_state": state,
            "available_headroom_q": max(0.0, round(c["max_capacity_q"] - (c["current_stock_q"] + c["incoming_booked_q"]), 2)),
            "live_queue_count": live_queue,
            "procured_count": procured_today,
            "is_locked": state == "Critical",
            "reroute_center": None
        }

        if state == "Critical":
            c_info["reroute_center"] = find_nearest_available_center(c, all_centers)

        enriched.append(c_info)

    conn.close()
    return enriched

@router.get("/evacuation-alerts")
def get_evacuation_alerts():
    """Retrieves all evacuation alerts with recommended truck counts and actions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT a.*, c.name as center_name, c.district, c.max_capacity_q, c.current_stock_q, c.incoming_booked_q
    FROM evacuation_alerts a
    JOIN procurement_centers c ON a.center_id = c.id
    ORDER BY a.status ASC, a.id DESC
    """)
    alerts = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return alerts

@router.post("/evacuation-alerts/{alert_id}/dispatch")
def dispatch_evacuation(alert_id: int, req: DispatchEvacuationRequest):
    """Marks an evacuation alert as dispatched and decrements excess stock from the center to buffer godown."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM evacuation_alerts WHERE id = ?", (alert_id,))
    alert = cursor.fetchone()

    if not alert:
        conn.close()
        raise HTTPException(status_code=404, detail="Alert not found.")

    # Decrement stock (each truck clears 100 Q)
    cleared_stock_q = req.trucks_dispatched * 100.0
    cursor.execute("SELECT current_stock_q FROM procurement_centers WHERE id = ?", (alert["center_id"],))
    curr = cursor.fetchone()
    if curr:
        new_curr = max(0.0, curr["current_stock_q"] - cleared_stock_q)
        cursor.execute("UPDATE procurement_centers SET current_stock_q = ? WHERE id = ?", (new_curr, alert["center_id"]))

    cursor.execute("""
    UPDATE evacuation_alerts 
    SET status = 'DISPATCHED', updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (alert_id,))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "alert_id": alert_id,
        "trucks_dispatched": req.trucks_dispatched,
        "stock_cleared_q": cleared_stock_q,
        "message": f"Logistics evacuation dispatched! {req.trucks_dispatched} trucks assigned to clear {cleared_stock_q} Q."
    }

@router.get("/system-intelligence")
def get_system_intelligence():
    """
    Comprehensive System Intelligence panel data (PRD FR28):
    1. Queue Intelligence
    2. Storage Intelligence
    3. Equity Engine Compliance
    4. AI Quality Inspection Analytics
    5. Offline Sync Monitor
    6. Logistics & Evacuation Automation
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Queue Intelligence: Hourly arrival distribution
    cursor.execute("""
    SELECT arrival_window_start, arrival_window_end, COUNT(*) as count, SUM(allocated_weight_q) as total_weight
    FROM slots
    WHERE status NOT IN ('REJECTED', 'REROUTED')
    GROUP BY arrival_window_start, arrival_window_end
    ORDER BY arrival_window_start ASC
    """)
    queue_dist = [dict(r) for r in cursor.fetchall()]

    # 2. Storage Intelligence: High level godown summary
    cursor.execute("""
    SELECT 
        SUM(max_capacity_q) as total_capacity,
        SUM(current_stock_q) as total_stock,
        SUM(incoming_booked_q) as total_incoming
    FROM procurement_centers
    """)
    st = dict(cursor.fetchone())
    district_s_fill = calculate_s_fill(st["total_stock"] or 0, st["total_incoming"] or 0, st["total_capacity"] or 1)

    # 3. Equity Engine: Small vs Large farmer volume distribution
    cursor.execute("""
    SELECT 
        u.farmer_category,
        COUNT(s.id) as booking_count,
        SUM(s.allocated_weight_q) as total_weight_q
    FROM slots s
    JOIN users u ON s.farmer_id = u.id
    GROUP BY u.farmer_category
    """)
    equity_breakdown = [dict(r) for r in cursor.fetchall()]

    # Auto-tranche audit: count slots with total_tranches > 1
    cursor.execute("SELECT COUNT(*) as tranche_bookings, SUM(allocated_weight_q) as tranches_volume FROM slots WHERE total_tranches > 1")
    tranche_stats = dict(cursor.fetchone())

    # 4. AI Quality Lab: Grade Distribution & Average Moisture
    cursor.execute("""
    SELECT 
        final_grade,
        COUNT(*) as count,
        AVG(moisture_percentage) as avg_moisture,
        AVG(discoloration_percentage) as avg_discoloration
    FROM quality_inspections
    GROUP BY final_grade
    """)
    quality_stats = [dict(r) for r in cursor.fetchall()]

    # 5. Offline Sync Nodes Status
    cursor.execute("SELECT * FROM offline_transactions ORDER BY id DESC LIMIT 10")
    recent_syncs = [dict(r) for r in cursor.fetchall()]

    # 6. Active Alerts Count
    cursor.execute("SELECT * FROM evacuation_alerts ORDER BY id DESC LIMIT 5")
    recent_alerts = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "queue_intelligence": {
            "window_distribution": queue_dist,
            "smoothing_algorithm": "Dynamic 2-Hour Window Throughput Balancer with Distance & Small-Farmer Priority"
        },
        "storage_intelligence": {
            "total_district_capacity_q": st["total_capacity"],
            "total_district_stock_q": st["total_stock"],
            "total_district_incoming_q": st["total_incoming"],
            "district_s_fill_percentage": district_s_fill,
            "thresholds": {"safe": "<80%", "warning": "80-95%", "critical": ">=95%"}
        },
        "equity_engine": {
            "breakdown": equity_breakdown,
            "tranching_audit": tranche_stats,
            "rule_enforcement": "40% Daily Center Capacity Guaranteed for Small Farmers (<=5 Acres) + 50Q Daily Capping"
        },
        "quality_intelligence": {
            "inspections_breakdown": quality_stats,
            "model_type": "Heuristic Computer Vision (Pillow RGB / Optical Saturation Analyzer)",
            "classification_notice": "AI-assisted preliminary assessment (non-laboratory)"
        },
        "offline_sync_monitor": {
            "total_synced_records": len(recent_syncs),
            "recent_syncs": recent_syncs,
            "deduplication_mode": "Idempotent UUID with Server-side Existence Check"
        },
        "logistics_automation": {
            "recent_alerts": recent_alerts,
            "truck_capacity_standard_q": 100.0,
            "auto_trigger_rule": "S_fill >= 80% with Nearest Depot Route Calculation"
        }
    }

@router.post("/reset-demo-data")
def reset_all_demo_data():
    """Resets database state with pristine demo data for judges."""
    seed_demo_data()
    return {"status": "success", "message": "Demo data refreshed to default pristine state."}
