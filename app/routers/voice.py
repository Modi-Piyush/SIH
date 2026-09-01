"""
Voice Router: Hindi IVR & Feature-Phone Dialogue Simulator.
Allows low-literacy and non-smartphone farmers to register and book slots
through conversational Hindi voice or keypad simulation.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.procurement_engine import calculate_crop_weight, is_small_farmer
from app.routers.farmer import book_slot, BookSlotRequest, register_or_login, FarmerRegisterRequest

router = APIRouter(prefix="/api/voice", tags=["Hindi Voice IVR"])

class IVRStepRequest(BaseModel):
    session_id: str
    step: int = 1
    phone: Optional[str] = "9876543210"
    farmer_name: Optional[str] = "रामेश कुमार"
    village: Optional[str] = "रामपुर कलां"
    crop_name: Optional[str] = "Wheat"
    land_acres: Optional[float] = 3.0
    center_id: Optional[int] = 1
    input_text: Optional[str] = None
    dtmf_key: Optional[str] = None

@router.post("/interactive-session")
def process_ivr_step(req: IVRStepRequest):
    """
    Processes interactive Hindi IVR steps for feature phone simulator:
    - Step 1: Welcome & Farmer Phone/Name prompt
    - Step 2: Crop selection (1 for Gehun, 2 for Chana, 3 for Tur, 4 for Dhan)
    - Step 3: Land area input & automatic yield calculation
    - Step 4: Center selection & Live booking confirmation with token and SMS
    """
    if req.step == 1:
        return {
            "session_id": req.session_id,
            "current_step": 1,
            "next_step": 2,
            "prompt_hindi": "नमस्ते! सरकारी ई-खरीद किसान सेवा में आपका स्वागत है। कृपया अपनी फसल चुनने के लिए 1 दबाएं या बोलें।",
            "prompt_english": "Welcome to Government e-Procurement Kisan IVR. Please press 1 or speak to select your crop.",
            "options": [
                {"key": "1", "label": "गेहूं (Wheat)"},
                {"key": "2", "label": "चना (Chana)"},
                {"key": "3", "label": "तुअर / अरहर (Tur)"},
                {"key": "4", "label": "धान (Paddy)"}
            ]
        }

    elif req.step == 2:
        crop_map = {"1": "Wheat", "2": "Chana", "3": "Tur", "4": "Paddy"}
        selected_crop = crop_map.get(req.dtmf_key or "1", req.crop_name or "Wheat")

        return {
            "session_id": req.session_id,
            "current_step": 2,
            "next_step": 3,
            "selected_crop": selected_crop,
            "prompt_hindi": f"आपने {selected_crop} फसल चुनी है। कृपया अपनी जमीन का रकबा (एकड़ में) बताएं या दर्ज करें।",
            "prompt_english": f"You selected {selected_crop}. Please enter your land area in acres.",
            "options": [
                {"key": "2", "label": "2 एकड़"},
                {"key": "3", "label": "3.5 एकड़"},
                {"key": "5", "label": "5 एकड़"},
                {"key": "10", "label": "10 एकड़ (बड़ा किसान)"}
            ]
        }

    elif req.step == 3:
        acres = float(req.dtmf_key or req.land_acres or 3.0)
        crop = req.crop_name or "Wheat"
        estimated_weight = calculate_crop_weight(crop, acres)
        is_small = is_small_farmer(acres)

        return {
            "session_id": req.session_id,
            "current_step": 3,
            "next_step": 4,
            "selected_crop": crop,
            "land_acres": acres,
            "estimated_weight_q": estimated_weight,
            "is_small_farmer": is_small,
            "prompt_hindi": f"आपकी {acres} एकड़ जमीन के लिए अनुमानित उपज {estimated_weight} क्विंटल है। रामपुर क्रय केंद्र पर स्लॉट बुक करने के लिए 1 दबाएं।",
            "prompt_english": f"Estimated yield is {estimated_weight} Quintals. Press 1 to confirm booking at Rampur Center.",
            "options": [
                {"key": "1", "label": "रामपुर क्रय केंद्र (Rampur PACS)"},
                {"key": "2", "label": "कल्याणपुर बफर डिपो (Kalyanpur Depot)"}
            ]
        }

    elif req.step == 4:
        # Execute booking
        phone = req.phone or "9876543210"
        name = req.farmer_name or "रामेश कुमार"
        village = req.village or "रामपुर कलां"
        crop = req.crop_name or "Wheat"
        acres = float(req.land_acres or 3.0)
        center_id = req.center_id or 1

        # Auto register / login farmer
        reg_res = register_or_login(FarmerRegisterRequest(
            phone=phone,
            name=name,
            village=village,
            land_acres=acres
        ))

        # Book slot
        book_res = book_slot(BookSlotRequest(
            phone=phone,
            center_id=center_id,
            crop_name=crop,
            land_acres=acres,
            weight_input_mode="ESTIMATE"
        ))

        token_code = book_res["primary_token"]
        window = book_res["queue_info"]["window"]

        return {
            "session_id": req.session_id,
            "current_step": 4,
            "next_step": 5,
            "completed": True,
            "token_code": token_code,
            "arrival_window": window,
            "prompt_hindi": f"बधाई हो {name}! आपका स्लॉट सफलतापूर्वक बुक हो गया है। आपका टोकन नंबर है {token_code}। कृपया समय {window} पर केंद्र पहुंचें। एसएमएस भेज दिया गया है। धन्यवाद!",
            "prompt_english": f"Congratulations! Your booking is confirmed with Token {token_code}. Arrival window is {window}. SMS notification dispatched.",
            "booking_details": book_res
        }

    else:
        return {
            "session_id": req.session_id,
            "current_step": req.step,
            "prompt_hindi": "धन्यवाद! ई-खरीद सेवा का उपयोग करने के लिए आभार।",
            "prompt_english": "Thank you for using e-Procurement Voice Service."
        }
