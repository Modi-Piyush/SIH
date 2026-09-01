"""
Storage Engine: Real-time Storage-Aware Admission Control, S_fill Calculation,
Safe/Warning/Critical States, Evacuation Alerts, and 15km Nearest-Center Rerouting.
"""

import math
from typing import Dict, Any, List, Optional, Tuple

SAFE_THRESHOLD = 80.0       # < 80% is Safe
CRITICAL_THRESHOLD = 95.0   # >= 95% is Critical (Locked)
TRUCK_CAPACITY_Q = 100.0    # 10 Tonnes = 100 Quintals per standard evacuation truck
MAX_REROUTE_RADIUS_KM = 15.0

def calculate_s_fill(current_stock_q: float, incoming_booked_q: float, max_capacity_q: float) -> float:
    """
    Computes storage utilization percentage according to PRD Section 6.3:
    S_fill = (Current Stock + Incoming Booked Stock) / Maximum Godown Capacity * 100
    """
    if max_capacity_q <= 0:
        return 100.0
    s_fill = ((current_stock_q + incoming_booked_q) / max_capacity_q) * 100.0
    return round(s_fill, 2)

def evaluate_storage_state(s_fill: float) -> str:
    """Returns 'Safe', 'Warning', or 'Critical' based on S_fill."""
    if s_fill < SAFE_THRESHOLD:
        return "Safe"
    elif s_fill < CRITICAL_THRESHOLD:
        return "Warning"
    else:
        return "Critical"

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two geographic coordinates in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

def find_nearest_available_center(
    current_center: Dict[str, Any],
    all_centers: List[Dict[str, Any]],
    requested_weight_q: float = 50.0,
    max_radius_km: float = MAX_REROUTE_RADIUS_KM
) -> Optional[Dict[str, Any]]:
    """
    Finds the nearest alternative procurement center within max_radius_km
    that has available storage capacity (< 85% S_fill) and active status.
    """
    origin_lat = current_center["lat"]
    origin_lng = current_center["lng"]
    current_id = current_center["id"]

    candidates = []

    for center in all_centers:
        if center["id"] == current_id or center.get("status") != "ACTIVE":
            continue

        c_stock = center["current_stock_q"]
        c_incoming = center["incoming_booked_q"]
        c_max = center["max_capacity_q"]
        s_fill = calculate_s_fill(c_stock, c_incoming, c_max)

        # Candidate must not be in critical/overloaded state
        if s_fill < 85.0:
            dist = haversine_distance_km(origin_lat, origin_lng, center["lat"], center["lng"])
            if dist <= max_radius_km:
                candidates.append({
                    "center": center,
                    "distance_km": dist,
                    "s_fill": s_fill,
                    "available_capacity_q": round(c_max - (c_stock + c_incoming), 2)
                })

    if not candidates:
        return None

    # Sort by distance
    candidates.sort(key=lambda x: x["distance_km"])
    nearest = candidates[0]
    
    return {
        "id": nearest["center"]["id"],
        "name": nearest["center"]["name"],
        "code": nearest["center"]["code"],
        "district": nearest["center"]["district"],
        "distance_km": nearest["distance_km"],
        "s_fill": nearest["s_fill"],
        "available_capacity_q": nearest["available_capacity_q"],
        "message": f"Recommended alternative: {nearest['center']['name']} ({nearest['distance_km']} km away, {nearest['s_fill']}% storage used)."
    }

def generate_evacuation_recommendation(
    center_id: int,
    center_name: str,
    s_fill: float,
    current_stock_q: float,
    incoming_booked_q: float,
    max_capacity_q: float,
    nearest_depot_name: str = "Central Buffer Depot"
) -> Optional[Dict[str, Any]]:
    """
    Generates an automated evacuation alert if S_fill >= 80%.
    Computes excess stock relative to 75% target safe baseline and calculates required trucks.
    """
    if s_fill < SAFE_THRESHOLD:
        return None

    target_stock_q = max_capacity_q * 0.75
    total_effective_stock_q = current_stock_q + incoming_booked_q
    excess_stock_q = max(0.0, total_effective_stock_q - target_stock_q)

    # 1 truck = 100 Quintals (10 MT)
    recommended_trucks = max(1, math.ceil(excess_stock_q / TRUCK_CAPACITY_Q))

    trigger_reason = (
        f"Storage capacity crossed {SAFE_THRESHOLD}% Warning threshold "
        f"(Current S_fill: {s_fill}% with {total_effective_stock_q:.1f} Q booked/stored against {max_capacity_q:.1f} Q capacity)."
    )

    return {
        "center_id": center_id,
        "center_name": center_name,
        "current_fill_percentage": s_fill,
        "excess_stock_q": round(excess_stock_q, 1),
        "recommended_trucks": recommended_trucks,
        "recommended_destination": nearest_depot_name,
        "trigger_reason": trigger_reason,
        "action_required": f"Dispatch {recommended_trucks} evacuation trucks ({recommended_trucks * 10} MT) to {nearest_depot_name} to restore safe operating headroom."
    }
