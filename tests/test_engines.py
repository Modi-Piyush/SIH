"""
Comprehensive Automated Test Suite for SIH PS 26032:
Tests Business Logic Engines, Storage Admission Rules, Social Equity Rules,
Quality Inspection, Offline Deduplication Sync, and End-to-End API Workflows.
"""

import os
import sys
import unittest
from datetime import date
from io import BytesIO
from PIL import Image

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db, seed_demo_data, get_db_connection
from app.services.procurement_engine import (
    CROP_MULTIPLIERS, calculate_crop_weight, is_small_farmer,
    generate_tranches, check_social_equity_quota, validate_weighment_tolerance,
    calculate_payment_breakdown
)
from app.services.storage_engine import (
    calculate_s_fill, evaluate_storage_state, haversine_distance_km,
    find_nearest_available_center, generate_evacuation_recommendation
)
from app.services.queue_engine import allocate_optimal_arrival_window
from app.services.quality_engine import analyze_crop_image, get_simulated_sample_inspection
from fastapi.testclient import TestClient
from app.main import app

class TestProcurementEngines(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        seed_demo_data()
        cls.client = TestClient(app)

    # 1. Test Crop Multipliers & Weight Estimation
    def test_crop_multipliers(self):
        # Pulses
        self.assertEqual(calculate_crop_weight("Tur", 5.0), 40.0)      # 5 * 8
        self.assertEqual(calculate_crop_weight("Chana", 4.0), 32.0)    # 4 * 8
        self.assertEqual(calculate_crop_weight("Masoor", 2.0), 14.0)   # 2 * 7
        self.assertEqual(calculate_crop_weight("Moong", 2.0), 13.0)    # 2 * 6.5
        self.assertEqual(calculate_crop_weight("Urad", 2.0), 13.0)     # 2 * 6.5
        # Grains
        self.assertEqual(calculate_crop_weight("Wheat", 3.0), 54.0)    # 3 * 18
        self.assertEqual(calculate_crop_weight("Paddy", 2.0), 40.0)    # 2 * 20
        self.assertEqual(calculate_crop_weight("Maize", 2.0), 32.0)    # 2 * 16
        self.assertEqual(calculate_crop_weight("Bajra", 2.0), 24.0)    # 2 * 12
        self.assertEqual(calculate_crop_weight("Jowar", 2.0), 20.0)    # 2 * 10

    # 2. Test Social Equity & Auto-Tranching Boundaries
    def test_social_equity_classification(self):
        self.assertTrue(is_small_farmer(0.5))
        self.assertTrue(is_small_farmer(5.0))   # Boundary: exactly 5 acres is small
        self.assertFalse(is_small_farmer(5.1))  # >5 acres is large
        self.assertFalse(is_small_farmer(15.0))

    def test_50q_daily_cap_and_auto_tranching(self):
        # Exactly 50 Q -> Single tranche
        t50 = generate_tranches(50.0)
        self.assertEqual(len(t50), 1)
        self.assertEqual(t50[0]["allocated_weight_q"], 50.0)

        # 51 Q -> 2 tranches (50 Q + 1 Q)
        t51 = generate_tranches(51.0)
        self.assertEqual(len(t51), 2)
        self.assertEqual(t51[0]["allocated_weight_q"], 50.0)
        self.assertEqual(t51[1]["allocated_weight_q"], 1.0)

        # 120 Q -> 3 tranches (50 Q + 50 Q + 20 Q)
        t120 = generate_tranches(120.0)
        self.assertEqual(len(t120), 3)
        self.assertEqual(t120[0]["allocated_weight_q"], 50.0)
        self.assertEqual(t120[1]["allocated_weight_q"], 50.0)
        self.assertEqual(t120[2]["allocated_weight_q"], 20.0)

    def test_social_equity_quota_enforcement(self):
        daily_cap = 600.0
        # Small farmer allowed
        allowed, msg = check_social_equity_quota(
            land_acres=3.0, requested_weight_q=40.0, daily_cap_q=daily_cap,
            small_farmer_booked_q=100.0, general_booked_q=200.0
        )
        self.assertTrue(allowed)

        # Large farmer trying to book when general quota is full (general pool = 360Q, booked = 350Q, requesting 50Q)
        allowed, msg = check_social_equity_quota(
            land_acres=10.0, requested_weight_q=50.0, daily_cap_q=daily_cap,
            small_farmer_booked_q=100.0, general_booked_q=350.0
        )
        self.assertFalse(allowed)
        self.assertIn("General quota", msg)

    # 3. Test Storage Engine (S_fill, Safe/Warning/Critical, Evacuation & Rerouting)
    def test_storage_fill_and_states(self):
        # Safe (<80%)
        s_fill_safe = calculate_s_fill(current_stock_q=500.0, incoming_booked_q=200.0, max_capacity_q=1000.0)
        self.assertEqual(s_fill_safe, 70.0)
        self.assertEqual(evaluate_storage_state(s_fill_safe), "Safe")

        # Warning (80% - 94.9%)
        s_fill_warn = calculate_s_fill(current_stock_q=800.0, incoming_booked_q=50.0, max_capacity_q=1000.0)
        self.assertEqual(s_fill_warn, 85.0)
        self.assertEqual(evaluate_storage_state(s_fill_warn), "Warning")

        # Critical (>=95%)
        s_fill_crit = calculate_s_fill(current_stock_q=920.0, incoming_booked_q=40.0, max_capacity_q=1000.0)
        self.assertEqual(s_fill_crit, 96.0)
        self.assertEqual(evaluate_storage_state(s_fill_crit), "Critical")

    def test_evacuation_alert_generation(self):
        evac = generate_evacuation_recommendation(
            center_id=2, center_name="Bilaspur PACS", s_fill=85.0,
            current_stock_q=800.0, incoming_booked_q=50.0, max_capacity_q=1000.0,
            nearest_depot_name="Kalyanpur Depot"
        )
        self.assertIsNotNone(evac)
        self.assertEqual(evac["recommended_trucks"], 1)  # (850 - 750) = 100 Q / 100 Q = 1 truck

    def test_nearest_center_rerouting(self):
        sitapur = {"id": 3, "name": "Sitapur Godown", "lat": 25.2890, "lng": 83.0150}
        all_centers = [
            {"id": 1, "name": "Rampur PACS", "code": "P-1", "district": "Varanasi", "lat": 25.3176, "lng": 82.9739, "current_stock_q": 750, "incoming_booked_q": 150, "max_capacity_q": 2000, "status": "ACTIVE"},
            {"id": 3, "name": "Sitapur Godown", "code": "P-3", "district": "Varanasi", "lat": 25.2890, "lng": 83.0150, "current_stock_q": 920, "incoming_booked_q": 40, "max_capacity_q": 1000, "status": "ACTIVE"},
            {"id": 4, "name": "Kalyanpur Depot", "code": "P-4", "district": "Varanasi", "lat": 25.3340, "lng": 83.0520, "current_stock_q": 800, "incoming_booked_q": 200, "max_capacity_q": 3000, "status": "ACTIVE"}
        ]
        nearest = find_nearest_available_center(sitapur, all_centers, requested_weight_q=50.0)
        self.assertIsNotNone(nearest)
        self.assertIn(nearest["id"], [1, 4])
        self.assertLessEqual(nearest["distance_km"], 15.0)

    # 4. Test Queue Engine (Arrival Windows)
    def test_arrival_window_allocation(self):
        by_window = {
            "08:00-10:00": [{"allocated_weight_q": 50.0}],
            "10:00-12:00": [{"allocated_weight_q": 120.0}]
        }
        res = allocate_optimal_arrival_window(by_window, allocated_weight_q=40.0, is_small_farmer=True)
        self.assertIn("arrival_window_start", res)
        self.assertIn("arrival_window_end", res)

    # 5. Test Quality Engine (Image Analysis & Heuristic Grading)
    def test_quality_analysis(self):
        # Create a test synthetic RGB image in memory
        img = Image.new("RGB", (100, 100), color=(180, 160, 120))
        buf = BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        result = analyze_crop_image(buf.getvalue(), crop_name="Wheat")
        self.assertTrue(result["is_preliminary_assessment"])
        self.assertIn("moisture_percentage", result)
        self.assertIn(result["ai_grade"], ["A", "B", "REJECTED"])

        # Preset simulations
        dry_sample = get_simulated_sample_inspection("dry_wheat", "Wheat")
        self.assertEqual(dry_sample["ai_grade"], "A")
        self.assertLess(dry_sample["moisture_percentage"], 14.5)

        wet_sample = get_simulated_sample_inspection("wet_grain", "Wheat")
        self.assertEqual(wet_sample["ai_grade"], "REJECTED")
        self.assertGreater(wet_sample["moisture_percentage"], 16.5)

    # 6. Test Weighment Tolerance
    def test_weighment_tolerance(self):
        # Exact match
        tol1 = validate_weighment_tolerance(50.0, 50.0)
        self.assertFalse(tol1["is_mismatch_flagged"])

        # +10% within tolerance
        tol2 = validate_weighment_tolerance(50.0, 55.0)
        self.assertFalse(tol2["is_mismatch_flagged"])

        # +20% exceeds tolerance
        tol3 = validate_weighment_tolerance(50.0, 60.0)
        self.assertTrue(tol3["is_mismatch_flagged"])

    # 7. Test Idempotent Offline Sync Deduplication (FR16)
    def test_idempotent_offline_sync(self):
        payload = {
            "device_id": "GATE-TAB-01",
            "transactions": [
                {
                    "client_tx_id": "UUID-TEST-9999",
                    "sync_type": "CHECK_IN",
                    "token_code": "TK-78401",
                    "payload": {"tractor_number": "UP-65-TEST-99"},
                    "client_timestamp": "2026-09-01T10:00:00Z"
                }
            ]
        }

        # First sync call -> should succeed
        res1 = self.client.post("/api/guard/sync-offline-transactions", json=payload)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1["synced_count"], 1)
        self.assertEqual(data1["duplicate_count"], 0)

        # Second sync call with exact same client_tx_id -> should be recognized as duplicate and skipped
        res2 = self.client.post("/api/guard/sync-offline-transactions", json=payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["synced_count"], 0)
        self.assertEqual(data2["duplicate_count"], 1)
        self.assertEqual(data2["results"][0]["status"], "DUPLICATE_SKIPPED")

    # 8. Full End-to-End API Flow Test (Registration -> Booking -> CheckIn -> Quality -> Accept -> Admin Metrics)
    def test_full_e2e_procurement_workflow(self):
        # Step A: Register Farmer
        reg = self.client.post("/api/farmer/register-or-login", json={
            "phone": "9812345678",
            "name": "Kisan Test",
            "village": "Varanasi Gram",
            "land_acres": 3.0
        })
        self.assertEqual(reg.status_code, 200)
        self.assertTrue(reg.json()["is_small_farmer"])

        # Step B: Book Slot at Rampur Center (ID 1)
        book = self.client.post("/api/farmer/book-slot", json={
            "phone": "9812345678",
            "center_id": 1,
            "crop_name": "Wheat",
            "land_acres": 3.0,
            "weight_input_mode": "ESTIMATE"
        })
        self.assertEqual(book.status_code, 200)
        token_code = book.json()["primary_token"]
        self.assertTrue(token_code.startswith("TK-"))

        # Step C: Gate Check-in
        checkin = self.client.post("/api/guard/check-in", json={
            "token_code": token_code,
            "tractor_number": "UP-65-TEST-1234"
        })
        self.assertEqual(checkin.status_code, 200)
        self.assertEqual(checkin.json()["new_status"], "CHECKED_IN")

        # Step D: Mandi Clerk Accepts Crop & Fulfills Delivery (Atomic FR22)
        fulfill = self.client.post("/api/clerk/accept-and-fulfill", json={
            "token_code": token_code,
            "gross_weight_q": 74.0,
            "tare_weight_q": 20.0,
            "moisture_percentage": 12.5,
            "ai_grade": "A",
            "final_grade": "A",
            "inspector_notes": "Clean high grade wheat."
        })
        self.assertEqual(fulfill.status_code, 200)
        f_data = fulfill.json()
        self.assertEqual(f_data["action"], "ACCEPT_AND_FULFILL_COMPLETE")
        self.assertEqual(f_data["net_weight_q"], 54.0)
        self.assertTrue(f_data["receipt_number"].startswith("REC-"))
        self.assertTrue(f_data["transaction_ref"].startswith("TXN-DBT-"))

        # Step E: Verify Token Live Status is PAYMENT_DISPATCHED
        tok = self.client.get(f"/api/farmer/tokens/{token_code}")
        self.assertEqual(tok.status_code, 200)
        self.assertEqual(tok.json()["status"], "PAYMENT_DISPATCHED")
        self.assertIsNotNone(tok.json()["receipt"])
        self.assertIsNotNone(tok.json()["payment"])

        # Step F: Admin Metrics updated
        metrics = self.client.get("/api/admin/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertGreater(metrics.json()["total_procured_q"], 0)
        self.assertGreater(metrics.json()["total_payout_inr"], 0)

    # 9. Test Exact Weight Mode in Calculation and Booking
    def test_exact_weight_mode(self):
        # Calculation with EXACT mode
        calc_res = self.client.post("/api/farmer/calculate-weight", json={
            "crop_name": "Wheat",
            "land_acres": 4.0,
            "mode": "EXACT",
            "exact_weight_q": 35.5
        })
        self.assertEqual(calc_res.status_code, 200)
        calc_data = calc_res.json()
        self.assertEqual(calc_data["total_weight_q"], 35.5)
        self.assertEqual(calc_data["estimated_weight_q"], 72.0) # 4 * 18

        # Ensure farmer is registered
        self.client.post("/api/farmer/register-or-login", json={
            "phone": "9812345679",
            "name": "Exact Kisan",
            "village": "Rampur",
            "land_acres": 4.0
        })

        # Booking with EXACT mode
        book_res = self.client.post("/api/farmer/book-slot", json={
            "phone": "9812345679",
            "center_id": 1,
            "crop_name": "Wheat",
            "land_acres": 4.0,
            "weight_input_mode": "EXACT",
            "requested_weight_q": 35.5
        })
        self.assertEqual(book_res.status_code, 200)
        book_data = book_res.json()
        self.assertEqual(book_data["total_weight_q"], 35.5)

if __name__ == "__main__":
    unittest.main()

