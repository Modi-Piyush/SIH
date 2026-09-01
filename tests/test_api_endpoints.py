"""
Live HTTP Endpoint Verification Script for Running Server
"""

import httpx

def verify_live_server():
    base_url = "http://127.0.0.1:8000"
    client = httpx.Client(base_url=base_url, timeout=10.0)

    print("Checking GET / ...")
    r = client.get("/")
    assert r.status_code == 200, f"Failed GET /: {r.status_code}"
    assert "e-Kisan Krishi Samridhi" in r.text
    print("  -> OK: Static HTML served.")

    print("Checking GET /api/health ...")
    r = client.get("/api/health")
    assert r.status_code == 200
    print("  -> OK:", r.json())

    print("Checking GET /api/farmer/centers ...")
    r = client.get("/api/farmer/centers")
    assert r.status_code == 200
    centers = r.json()
    print(f"  -> OK: Loaded {len(centers)} PACS centers. S_fill values:", [c["s_fill_percentage"] for c in centers])

    print("Checking POST /api/farmer/calculate-weight ...")
    r = client.post("/api/farmer/calculate-weight", json={"crop_name": "Wheat", "land_acres": 3.5, "mode": "ESTIMATE"})
    assert r.status_code == 200
    print("  -> OK:", r.json()["estimated_weight_q"], "Q, Gross Payout:", r.json()["estimated_gross_payout"])

    print("Checking POST /api/farmer/book-slot ...")
    r = client.post("/api/farmer/book-slot", json={
        "phone": "9876543210",
        "name": "Ramesh Kumar",
        "village": "Rampur",
        "center_id": 1,
        "crop_name": "Wheat",
        "land_acres": 3.5
    })
    assert r.status_code == 200
    data = r.json()
    token = data["primary_token"]
    print("  -> OK: Token issued:", token, "Arrival Window:", data["queue_info"]["window"])

    print(f"Checking GET /api/guard/verify-token/{token} ...")
    r = client.get(f"/api/guard/verify-token/{token}")
    assert r.status_code == 200
    print("  -> OK: Verified farmer:", r.json()["farmer_name"])

    print(f"Checking POST /api/guard/check-in for {token} ...")
    r = client.post("/api/guard/check-in", json={"token_code": token, "tractor_number": "UP-65-AB-9999"})
    assert r.status_code == 200
    print("  -> OK: Check-in response:", r.json()["new_status"])

    print("Checking GET /api/clerk/queue/1 ...")
    r = client.get("/api/clerk/queue/1")
    assert r.status_code == 200
    print("  -> OK: Clerk queue count:", len(r.json()))

    print("Checking POST /api/clerk/accept-and-fulfill ...")
    r = client.post("/api/clerk/accept-and-fulfill", json={
        "token_code": token,
        "gross_weight_q": 83.0,
        "tare_weight_q": 20.0,
        "moisture_percentage": 12.8,
        "ai_grade": "A",
        "final_grade": "A",
        "inspector_notes": "Grade A Wheat verified."
    })
    assert r.status_code == 200
    receipt = r.json()
    print("  -> OK: Receipt issued:", receipt["receipt_number"], "Net Payout:", receipt["payment_breakdown"]["net_payable_amount"])

    print("Checking GET /api/admin/metrics ...")
    r = client.get("/api/admin/metrics")
    assert r.status_code == 200
    print("  -> OK: Admin metrics:", r.json())

    print("Checking GET /api/admin/system-intelligence ...")
    r = client.get("/api/admin/system-intelligence")
    assert r.status_code == 200
    print("  -> OK: System intelligence keys:", list(r.json().keys()))

    print("Checking POST /api/voice/interactive-session ...")
    r = client.post("/api/voice/interactive-session", json={"session_id": "IVR-TEST-1", "step": 1})
    assert r.status_code == 200
    print("  -> OK: Voice IVR prompt:", r.json()["prompt_english"])

    print("\nALL 12 LIVE HTTP SERVER ENDPOINTS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    verify_live_server()
