"""
Procurement Engine: Enforces Crop Yield Multipliers, Social Equity Rules,
50-Quintal Daily Capping with Auto-Tranching, Tolerance Validation, and State Transitions.
"""

import math
from datetime import date, timedelta
from typing import Dict, Any, List, Tuple, Optional

# Section 6.1: Crop Multipliers (Q/Acre)
CROP_MULTIPLIERS: Dict[str, float] = {
    # Pulses
    "Tur": 8.0,
    "Chana": 8.0,
    "Masoor": 7.0,
    "Moong": 6.5,
    "Urad": 6.5,
    # Grains
    "Wheat": 18.0,
    "Paddy": 20.0,
    "Maize": 16.0,
    "Bajra": 12.0,
    "Jowar": 10.0
}

CROP_CATEGORIES: Dict[str, str] = {
    "Tur": "Pulses",
    "Chana": "Pulses",
    "Masoor": "Pulses",
    "Moong": "Pulses",
    "Urad": "Pulses",
    "Wheat": "Grains",
    "Paddy": "Grains",
    "Maize": "Grains",
    "Bajra": "Grains",
    "Jowar": "Grains"
}

# MSP Rates (INR per Quintal - Government 2024-2025/2026 Reference Rates)
CROP_MSP_RATES: Dict[str, float] = {
    "Wheat": 2275.0,
    "Paddy": 2300.0,
    "Maize": 2090.0,
    "Bajra": 2500.0,
    "Jowar": 3180.0,
    "Tur": 7550.0,
    "Chana": 5440.0,
    "Masoor": 6425.0,
    "Moong": 8558.0,
    "Urad": 6950.0
}

DAILY_CAP_PER_SLOT_Q = 50.0
SMALL_FARMER_ACRE_THRESHOLD = 5.0
SMALL_FARMER_RESERVATION_RATIO = 0.40  # 40% reserved
TOLERANCE_PERCENTAGE = 15.0            # ±15% tolerance

def is_small_farmer(land_acres: float) -> bool:
    """Classifies farmer based on landholding <= 5.0 acres."""
    return float(land_acres) <= SMALL_FARMER_ACRE_THRESHOLD

def calculate_crop_weight(crop_name: str, land_acres: float) -> float:
    """Calculates estimated weight in Quintals using crop multiplier."""
    if crop_name not in CROP_MULTIPLIERS:
        raise ValueError(f"Unknown crop: {crop_name}. Supported: {list(CROP_MULTIPLIERS.keys())}")
    multiplier = CROP_MULTIPLIERS[crop_name]
    return round(land_acres * multiplier, 2)

def generate_tranches(total_weight_q: float, start_date: Optional[date] = None, interval_days: int = 3) -> List[Dict[str, Any]]:
    """
    Applies the 50-Quintal daily cap with auto-tranching.
    Splits any quantity > 50 Q into sequential dated tranches spaced across days.
    E.g. 120 Q -> Tranche 1 (50 Q, Day 0), Tranche 2 (50 Q, Day +3), Tranche 3 (20 Q, Day +6).
    """
    if start_date is None:
        start_date = date.today()

    if total_weight_q <= DAILY_CAP_PER_SLOT_Q:
        return [{
            "tranche_number": 1,
            "total_tranches": 1,
            "allocated_weight_q": round(total_weight_q, 2),
            "scheduled_date": start_date.isoformat(),
            "reason": "Single tranche booking within 50Q daily cap"
        }]

    tranches = []
    remaining = total_weight_q
    tranche_num = 1
    total_tranches = math.ceil(total_weight_q / DAILY_CAP_PER_SLOT_Q)

    while remaining > 0:
        allocated = min(remaining, DAILY_CAP_PER_SLOT_Q)
        tranche_date = start_date + timedelta(days=(tranche_num - 1) * interval_days)
        tranches.append({
            "tranche_number": tranche_num,
            "total_tranches": total_tranches,
            "allocated_weight_q": round(allocated, 2),
            "scheduled_date": tranche_date.isoformat(),
            "reason": f"Tranche {tranche_num} of {total_tranches} (50Q daily cap rule applied)"
        })
        remaining = round(remaining - allocated, 2)
        tranche_num += 1

    return tranches

def check_social_equity_quota(
    land_acres: float,
    requested_weight_q: float,
    daily_cap_q: float,
    small_farmer_booked_q: float,
    general_booked_q: float
) -> Tuple[bool, str]:
    """
    Enforces the 40% small-farmer volume reservation.
    Small farmers can book from both reserved (40%) and general quota.
    Large farmers are strictly prohibited from dipping into the 40% small-farmer reservation.
    """
    small_reserved_q = daily_cap_q * SMALL_FARMER_RESERVATION_RATIO
    general_allowed_q = daily_cap_q * (1.0 - SMALL_FARMER_RESERVATION_RATIO)

    is_small = is_small_farmer(land_acres)

    if is_small:
        # Small farmer: can use remaining reserved quota or general quota
        total_remaining = daily_cap_q - (small_farmer_booked_q + general_booked_q)
        if requested_weight_q > total_remaining:
            return False, f"Daily center procurement capacity exhausted. Remaining: {total_remaining:.1f} Q."
        return True, "Small farmer reservation applied. Guaranteed procurement slot assigned."
    else:
        # Large farmer: restricted to general pool only
        general_remaining = general_allowed_q - general_booked_q
        if requested_weight_q > general_remaining:
            return False, f"General quota for large farmers exhausted for selected date. Remaining general capacity: {general_remaining:.1f} Q. (40% capacity is strictly reserved for small farmers)."
        return True, "General farmer quota available."

def validate_weighment_tolerance(estimated_weight_q: float, actual_net_weight_q: float) -> Dict[str, Any]:
    """
    Validates ±15% tolerance between weighbridge actual reading and estimated/booked weight.
    """
    if estimated_weight_q <= 0:
        deviation = 0.0
        mismatch = False
    else:
        deviation = round(((actual_net_weight_q - estimated_weight_q) / estimated_weight_q) * 100, 2)
        mismatch = abs(deviation) > TOLERANCE_PERCENTAGE

    return {
        "estimated_weight_q": estimated_weight_q,
        "actual_net_weight_q": actual_net_weight_q,
        "deviation_percentage": deviation,
        "is_mismatch_flagged": mismatch,
        "tolerance_limit_percentage": TOLERANCE_PERCENTAGE,
        "message": "Weighment within normal ±15% tolerance." if not mismatch else f"Warning: Weight deviation of {deviation:+.1f}% exceeds ±15% threshold."
    }

def calculate_payment_breakdown(crop_name: str, final_weight_q: float, quality_grade: str) -> Dict[str, Any]:
    """
    Calculates procurement payment breakdown with MSP rate, gross amount, quality deduction (if Grade B), and net amount.
    """
    msp_rate = CROP_MSP_RATES.get(crop_name, 2275.0)
    gross_amount = round(final_weight_q * msp_rate, 2)
    
    # Grade B has standard minor moisture refraction deduction (e.g. 1.5%), Grade A has 0% deduction
    deduction_rate = 0.015 if quality_grade == "B" else 0.0
    quality_deductions = round(gross_amount * deduction_rate, 2)
    net_payable = round(gross_amount - quality_deductions, 2)

    return {
        "crop_name": crop_name,
        "final_weight_q": final_weight_q,
        "msp_rate_per_q": msp_rate,
        "gross_amount": gross_amount,
        "quality_grade": quality_grade,
        "quality_deductions": quality_deductions,
        "net_payable_amount": net_payable
    }
