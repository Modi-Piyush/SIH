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

def calculate_payment_breakdown(
    crop_name: str,
    final_weight_q: float,
    quality_grade: str,
    moisture_percentage: float = 12.5,
    foreign_matter_percentage: float = 0.5,
    discoloration_percentage: float = 1.0
) -> Dict[str, Any]:
    """
    Calculates official procurement payment breakdown according to Government FAQ (Fair Average Quality) Refraction Norms:
    - Base MSP Gross Amount
    - Quality Refraction Cuts:
        * Moisture Cut: 0% for <=14.0%, 0.75% for 14.1%-15.0%, 1.5% for 15.1%-16.5%
        * Foreign Matter Cut: 0% for <=0.75%, proportional deduction for >0.75%
        * Discoloration Cut: 0.5% if >2.0%
        * Minimum 1.5% deduction for Grade B
    - Net DBT Payable to Farmer
    """
    msp_rate = CROP_MSP_RATES.get(crop_name, 2275.0)
    gross_amount = round(final_weight_q * msp_rate, 2)

    # 1. Moisture Refraction Cut (FCI Standard)
    if moisture_percentage <= 14.0:
        moisture_cut_pct = 0.0
    elif moisture_percentage <= 15.0:
        moisture_cut_pct = 0.0075  # 0.75%
    elif moisture_percentage <= 16.5:
        moisture_cut_pct = 0.015   # 1.5%
    else:
        moisture_cut_pct = 0.03    # 3.0% if accepted with override

    # 2. Foreign Matter Cut (> 0.75%)
    if foreign_matter_percentage > 0.75:
        foreign_cut_pct = min(0.05, round((foreign_matter_percentage - 0.75) / 100.0, 4))
    else:
        foreign_cut_pct = 0.0

    # 3. Discoloration Cut (> 2.0%)
    if discoloration_percentage > 2.0:
        discolor_cut_pct = 0.005  # 0.5%
    else:
        discolor_cut_pct = 0.0

    # Total refraction percentage
    total_refraction_pct = moisture_cut_pct + foreign_cut_pct + discolor_cut_pct
    if quality_grade == "B" and total_refraction_pct < 0.015:
        total_refraction_pct = 0.015  # Minimum 1.5% deduction for Grade B

    quality_deductions = round(gross_amount * total_refraction_pct, 2)
    net_payable = round(max(0.0, gross_amount - quality_deductions), 2)
    effective_rate = round(net_payable / final_weight_q, 2) if final_weight_q > 0 else msp_rate

    return {
        "crop_name": crop_name,
        "final_weight_q": final_weight_q,
        "msp_rate_per_q": msp_rate,
        "gross_amount": gross_amount,
        "quality_grade": quality_grade,
        "moisture_percentage": moisture_percentage,
        "moisture_cut_amount": round(gross_amount * moisture_cut_pct, 2),
        "foreign_matter_cut_amount": round(gross_amount * foreign_cut_pct, 2),
        "discoloration_cut_amount": round(gross_amount * discolor_cut_pct, 2),
        "total_refraction_percentage": round(total_refraction_pct * 100, 2),
        "quality_deductions": quality_deductions,
        "net_payable_amount": net_payable,
        "effective_rate_per_q": effective_rate
    }
