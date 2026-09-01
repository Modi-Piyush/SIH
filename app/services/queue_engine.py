"""
Queue Engine: Dynamic 2-Hour Arrival Window Allocation, Congestion Management,
Throughput Balancing, and Small-Farmer Priority Scheduling.
"""

from typing import List, Dict, Any, Tuple

DEFAULT_WINDOWS = [
    {"start": "08:00", "end": "10:00", "label": "Morning Slot 1 (08:00 AM - 10:00 AM)"},
    {"start": "10:00", "end": "12:00", "label": "Morning Slot 2 (10:00 AM - 12:00 PM)"},
    {"start": "12:00", "end": "14:00", "label": "Afternoon Slot 1 (12:00 PM - 02:00 PM)"},
    {"start": "14:00", "end": "16:00", "label": "Afternoon Slot 2 (02:00 PM - 04:00 PM)"},
    {"start": "16:00", "end": "18:00", "label": "Evening Slot (04:00 PM - 06:00 PM)"}
]

def allocate_optimal_arrival_window(
    existing_bookings_by_window: Dict[str, List[Dict[str, Any]]],
    allocated_weight_q: float,
    is_small_farmer: bool,
    weighbridge_speed_per_hr: float = 60.0,
    travel_distance_km: float = 5.0
) -> Dict[str, Any]:
    """
    Allocates an optimal 2-hour arrival window to balance traffic and smooth out congestion.
    - Weighbridge capacity per 2-hour window = weighbridge_speed_per_hr * 2 (Quintals)
    - If travel distance > 10 km, prefers slots from 10:00 AM onward.
    - Small farmers are prioritized for early/low-wait windows.
    """
    window_capacity_q = weighbridge_speed_per_hr * 2.0  # e.g., 60 Q/hr * 2 = 120 Q per window

    window_stats = []

    for w in DEFAULT_WINDOWS:
        w_key = f"{w['start']}-{w['end']}"
        bookings = existing_bookings_by_window.get(w_key, [])
        total_booked_weight = sum(b.get("allocated_weight_q", 0.0) for b in bookings)
        count = len(bookings)
        
        # Calculate load factor
        utilization_pct = (total_booked_weight / max(window_capacity_q, 1.0)) * 100.0
        
        # Distance penalty: if farmer is far (>10km), discourage 08:00-10:00
        distance_penalty = 30.0 if (w["start"] == "08:00" and travel_distance_km > 10.0) else 0.0
        
        # Small farmer priority bonus for early morning slots
        priority_bonus = 15.0 if (is_small_farmer and w["start"] in ["08:00", "10:00"]) else 0.0

        effective_score = utilization_pct + distance_penalty - priority_bonus

        window_stats.append({
            "window": w,
            "window_key": w_key,
            "count": count,
            "total_booked_weight_q": round(total_booked_weight, 2),
            "utilization_pct": round(utilization_pct, 1),
            "effective_score": effective_score,
            "available_q": max(0.0, round(window_capacity_q - total_booked_weight, 2))
        })

    # Pick window with the lowest effective score (least congestion)
    window_stats.sort(key=lambda x: x["effective_score"])
    selected = window_stats[0]

    return {
        "arrival_window_start": selected["window"]["start"],
        "arrival_window_end": selected["window"]["end"],
        "window_label": selected["window"]["label"],
        "estimated_queue_depth": selected["count"],
        "estimated_wait_minutes": max(5, selected["count"] * 10),
        "window_utilization_pct": selected["utilization_pct"],
        "all_windows_status": window_stats
    }

def get_live_center_queue_summary(slots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates queue statistics across status categories for live clerk & admin displays."""
    checked_in = [s for s in slots if s.get("status") == "CHECKED_IN"]
    quality_approved = [s for s in slots if s.get("status") == "QUALITY_APPROVED"]
    weighment_complete = [s for s in slots if s.get("status") == "WEIGHMENT_COMPLETE"]
    completed = [s for s in slots if s.get("status") == "PAYMENT_DISPATCHED"]

    return {
        "active_queue_length": len(checked_in),
        "quality_in_progress": len(quality_approved),
        "weighment_in_progress": len(weighment_complete),
        "completed_today": len(completed),
        "estimated_total_turnaround_time_mins": len(checked_in) * 12 + 10
    }
