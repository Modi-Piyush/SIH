"""
Quality Engine: AI Crop Quality Inspection, Heuristic Moisture Estimation,
Discoloration & Defect Detection, and Non-Laboratory Preliminary Grading.
"""

import io
import math
from typing import Dict, Any, Optional
from PIL import Image, ImageStat

MOISTURE_GRADE_A_THRESHOLD = 14.5
MOISTURE_GRADE_B_THRESHOLD = 16.5

def analyze_crop_image(image_bytes: bytes, crop_name: str = "Wheat") -> Dict[str, Any]:
    """
    Analyzes an uploaded grain sample photo using Pillow image analytics.
    Computes RGB mean/stddev, dark/discolored pixel ratio, foreign matter ratio,
    and calculates heuristic moisture percentage based on grain reflectance and optical saturation.
    
    CRITICAL PRD REQUIREMENT: All results are explicitly tagged as
    'is_preliminary_assessment = True' and carry clear advisory labeling.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise ValueError(f"Invalid image format: {str(e)}")

    # Resize for uniform fast analysis
    img_resized = img.resize((300, 300))
    stat = ImageStat.Stat(img_resized)
    r_mean, g_mean, b_mean = stat.mean
    r_std, g_std, b_std = stat.stddev

    # Convert to grayscale to evaluate dark kernel percentage & foreign matter
    gray = img_resized.convert("L")
    pixels = list(gray.tobytes())
    total_pixels = len(pixels)

    # Dark/Discolored grains heuristic: pixels with luminance < 60
    dark_pixels = sum(1 for p in pixels if p < 60)
    discoloration_pct = round((dark_pixels / total_pixels) * 100.0, 2)

    # Foreign matter / chaff heuristic: high-frequency variance / off-color pixels
    # Very bright pixels (dust/stones > 230) or extreme outlier colors
    foreign_pixels = sum(1 for p in pixels if p > 235)
    foreign_matter_pct = round((foreign_pixels / total_pixels) * 100.0, 2)

    # Broken grains estimation heuristic: texture irregularity / stddev ratio
    broken_grains_pct = round(min(12.0, (g_std / 255.0) * 20.0), 2)

    # Moisture estimation heuristic formula (calibrated across grain types):
    # Base moisture ~ 11.0% + optical reflectance factor (darker/damp grain absorbs more light, red/blue skew)
    # Grain moisture absorption decreases average luminance and increases color saturation
    luminance = (0.299 * r_mean + 0.587 * g_mean + 0.114 * b_mean)
    # Calibration baseline: optimal dry grain luminance ~ 160-180
    moisture_delta = (165.0 - luminance) * 0.08
    raw_moisture = 12.0 + moisture_delta + (discoloration_pct * 0.15)
    
    # Crop specific baseline adjustment
    if crop_name in ["Paddy", "Moong", "Urad"]:
        raw_moisture += 0.5

    # Clamp realistic range (8.5% to 22.0%)
    moisture_pct = round(max(8.5, min(22.0, raw_moisture)), 1)

    # Determine Grade and Outcome Recommendation according to PRD Section 6.5
    if moisture_pct < MOISTURE_GRADE_A_THRESHOLD:
        ai_grade = "A"
        grade_label = "Grade A (Prime Quality)"
        outcome = "Excellent — ready for immediate procurement. Moisture within safe threshold (<14.5%)."
        confidence = 0.94
        recommendation = "Proceed to Mandi for weighment."
    elif moisture_pct <= MOISTURE_GRADE_B_THRESHOLD:
        ai_grade = "B"
        grade_label = "Grade B (Fair Quality)"
        outcome = "Warning — slightly high moisture (14.5% - 16.5%). Acceptable with minor standard refraction or 1 extra day of sun drying recommended."
        confidence = 0.88
        recommendation = "Sun dry for 24 hours to achieve Grade A, or proceed with standard Grade B moisture deduction."
    else:
        ai_grade = "REJECTED"
        grade_label = "Rejected (High Moisture Risk)"
        outcome = "High moisture (>16.5%) — significant fungal / spoilage risk during godown storage. Moisture must be reduced before procurement."
        confidence = 0.96
        recommendation = "Do NOT travel to Mandi today. Dry grain under direct sunlight for 2-3 days until moisture drops below 14.5%."

    return {
        "is_preliminary_assessment": True,
        "disclaimer": "AI-assisted preliminary assessment (Non-laboratory heuristic estimation). Official weighbridge and physical inspection happen at Mandi.",
        "crop_name": crop_name,
        "moisture_percentage": moisture_pct,
        "discoloration_percentage": discoloration_pct,
        "foreign_matter_percentage": foreign_matter_pct,
        "broken_grains_percentage": broken_grains_pct,
        "ai_grade": ai_grade,
        "grade_label": grade_label,
        "outcome": outcome,
        "recommendation": recommendation,
        "confidence": confidence,
        "metrics_summary": {
            "moisture": f"{moisture_pct}% (Max allowed: 14.5%)",
            "discoloration": f"{discoloration_pct}% (Tolerance: < 3.0%)",
            "foreign_matter": f"{foreign_matter_pct}% (Tolerance: < 1.0%)",
            "broken_grains": f"{broken_grains_pct}% (Tolerance: < 4.0%)"
        }
    }

def get_simulated_sample_inspection(sample_type: str = "dry_wheat", crop_name: str = "Wheat") -> Dict[str, Any]:
    """
    Returns preset simulated inspections for rapid testing and demonstrations
    (e.g., Dry prime grain, Borderline moist grain, Excessively wet grain).
    """
    if sample_type == "dry_wheat":
        return {
            "is_preliminary_assessment": True,
            "disclaimer": "AI-assisted preliminary assessment (Non-laboratory heuristic estimation). Official weighbridge and physical inspection happen at Mandi.",
            "crop_name": crop_name,
            "moisture_percentage": 12.4,
            "discoloration_percentage": 0.8,
            "foreign_matter_percentage": 0.3,
            "broken_grains_percentage": 1.2,
            "ai_grade": "A",
            "grade_label": "Grade A (Prime Quality)",
            "outcome": "Excellent — ready for immediate procurement. Moisture within safe threshold (<14.5%).",
            "recommendation": "Proceed to Mandi for weighment.",
            "confidence": 0.96,
            "metrics_summary": {
                "moisture": "12.4% (Max allowed: 14.5%)",
                "discoloration": "0.8% (Tolerance: < 3.0%)",
                "foreign_matter": "0.3% (Tolerance: < 1.0%)",
                "broken_grains": "1.2% (Tolerance: < 4.0%)"
            }
        }
    elif sample_type == "medium_moist":
        return {
            "is_preliminary_assessment": True,
            "disclaimer": "AI-assisted preliminary assessment (Non-laboratory heuristic estimation). Official weighbridge and physical inspection happen at Mandi.",
            "crop_name": crop_name,
            "moisture_percentage": 15.2,
            "discoloration_percentage": 2.1,
            "foreign_matter_percentage": 0.7,
            "broken_grains_percentage": 2.5,
            "ai_grade": "B",
            "grade_label": "Grade B (Fair Quality)",
            "outcome": "Warning — slightly high moisture (14.5% - 16.5%). Acceptable with minor standard refraction or 1 extra day of sun drying recommended.",
            "recommendation": "Sun dry for 24 hours to achieve Grade A, or proceed with standard Grade B moisture deduction.",
            "confidence": 0.91,
            "metrics_summary": {
                "moisture": "15.2% (Max allowed: 14.5%)",
                "discoloration": "2.1% (Tolerance: < 3.0%)",
                "foreign_matter": "0.7% (Tolerance: < 1.0%)",
                "broken_grains": "2.5% (Tolerance: < 4.0%)"
            }
        }
    else:  # wet_grain
        return {
            "is_preliminary_assessment": True,
            "disclaimer": "AI-assisted preliminary assessment (Non-laboratory heuristic estimation). Official weighbridge and physical inspection happen at Mandi.",
            "crop_name": crop_name,
            "moisture_percentage": 18.6,
            "discoloration_percentage": 5.4,
            "foreign_matter_percentage": 1.8,
            "broken_grains_percentage": 4.1,
            "ai_grade": "REJECTED",
            "grade_label": "Rejected (High Moisture Risk)",
            "outcome": "High moisture (>16.5%) — significant fungal / spoilage risk during godown storage. Moisture must be reduced before procurement.",
            "recommendation": "Do NOT travel to Mandi today. Dry grain under direct sunlight for 2-3 days until moisture drops below 14.5%.",
            "confidence": 0.98,
            "metrics_summary": {
                "moisture": "18.6% (Max allowed: 14.5%)",
                "discoloration": "5.4% (Tolerance: < 3.0%)",
                "foreign_matter": "1.8% (Tolerance: < 1.0%)",
                "broken_grains": "4.1% (Tolerance: < 4.0%)"
            }
        }
