# Product Requirements Document (PRD)

## Smart Storage-Aware Farmer Procurement, AI Quality Inspection & Offline-Resilient Supply Chain Platform
**SIH Problem Statement:** PS 26032
**Document version:** 1.0
**Status:** Draft for hackathon build

---

## 1. Overview

### 1.1 Purpose
Government procurement centers (PACS) that buy crops directly from farmers currently run on manual, paper-based, or disconnected digital processes. This causes long farmer wait times, godown overflow, unfair advantage to large farmers, moisture-related rejections at the gate, and total system failure during rural internet outages.

This platform digitizes the end-to-end procurement journey — booking, gate entry, quality inspection, weighment, and payment — while explicitly engineering for three real-world constraints: **limited godown storage, unreliable connectivity, and inequitable access for smallholders.**

### 1.2 Product Vision
A single platform where a farmer can book a guaranteed 2-hour arrival slot from a phone call or a smartphone app, arrive to a fast and fair process, get an AI-assisted pre-check on crop moisture before wasting a trip, and trust that payment status is transparent — while government staff run every step (including check-in) even when the internet is down.

### 1.3 Success looks like
- Zero duplicate/lost transactions during an internet outage + reconnect cycle.
- No center ever accepts bookings past 95% storage capacity.
- Small farmers (≤5 acres) reliably get their guaranteed 40% share of daily volume.
- A farmer with excessively wet grain is warned *before* traveling to the mandi, not rejected at the gate.
- A judge can walk through the full flow (registration → booking → offline check-in → quality check → payment) in under 8 minutes.

---

## 2. Problem Statement

| Pain Point | Affected Role | Current Impact |
|---|---|---|
| No visibility into procurement schedule | Farmer | Wasted trips, long queues |
| Uncertainty on procurement/payment status | Farmer | Distrust, repeated inquiries |
| Godowns overfill during harvest peak | PACS/Admin | Forced shutdowns, spoilage |
| Excess moisture discovered only at the gate | Farmer | Rejected loads, wasted travel |
| Large farmers monopolize daily capacity | Small Farmer | Inequitable access |
| Rural internet outages | Guard/Clerk | Total operational stoppage |
| No feature-phone/voice access | Farmer (non-smartphone) | Digital exclusion |

---

## 3. Goals and Non-Goals

### 3.1 Goals
1. Smart, capacity-aware slot booking with 2-hour arrival windows.
2. Real-time, storage-aware admission control per procurement center.
3. Enforced small-farmer equity (40% volume reservation + 50-quintal daily cap with auto-tranching).
4. AI-assisted preliminary crop quality/moisture screening before gate arrival.
5. Fully offline-capable gate and mandi operations with automatic sync on reconnect.
6. Feature-phone/voice-based registration and booking simulation (Hindi).
7. End-to-end procurement and payment status transparency for farmers.
8. A government-grade, real-time district admin dashboard.

### 3.2 Non-Goals (out of scope for this prototype)
- Real telephony/SMS integration (Twilio/Exotel) — simulated only, with an integration-ready endpoint stub.
- Laboratory-grade moisture measurement — this is a heuristic CV estimator, explicitly labeled as such.
- Real payment gateway integration — payment status is tracked/simulated, not disbursed.
- Multi-district/multi-state scaling, load testing, or production security hardening.
- Native mobile apps (web-based, mobile-responsive only).

---

## 4. Users & Roles

| Role | Primary Device | Core Need |
|---|---|---|
| **Farmer** | Smartphone / feature phone / voice | Book a slot, know when to arrive, track status & payment |
| **Security Guard / Gatekeeper** | Tablet/mobile, often offline | Verify and check in farmers even without internet |
| **Mandi Clerk / Quality Inspector** | Desktop/tablet at center | Inspect quality, weigh, accept/reject, close procurement |
| **District Admin / DOCA** | Desktop | Monitor centers, storage, equity compliance, logistics in real time |

---

## 5. Functional Requirements

### 5.1 Farmer
- FR1: Register/login via Indian mobile number (`^[6-9]\d{9}$`), name, village, land area.
- FR2: Select crop (pulses or grains/cereals) from a fixed multiplier list.
- FR3: Choose weight input mode — (A) estimate from land area, or (B) enter exact quintals.
- FR4: Select a procurement center; system shows real-time storage status per center.
- FR5: Receive a system-recommended 2-hour arrival window based on live queue/capacity/travel distance.
- FR6: If requested quantity > 50 Q, system auto-splits into multiple dated tranche bookings.
- FR7: Receive a digital token (QR/token code, `TK-XXXXX`) with all booking details.
- FR8: Track live status: `CONFIRMED → CHECKED_IN → QUALITY_APPROVED → WEIGHMENT_COMPLETE → PAYMENT_DISPATCHED`, plus `REJECTED` / `REROUTED`.
- FR9: View procurement history and payment status.
- FR10: Receive simulated SMS notifications at key status changes.
- FR11: Access all of the above via a Hindi voice/feature-phone simulator as an alternative to the smartphone UI.

### 5.2 Security Guard / Gatekeeper
- FR12: Search/scan a token to verify a booking.
- FR13: Verify farmer identity and tractor number.
- FR14: Perform gate check-in, updating status to `CHECKED_IN`.
- FR15: Operate fully offline: verify against locally cached data, check in, and queue the transaction in IndexedDB with a "Pending Sync" indicator.
- FR16: Auto-detect reconnection and sync all pending transactions via `POST /api/sync-offline-transactions`, deduplicating on transaction ID.
- FR17: Display connectivity state (Online/Offline) and sync state (Offline / Syncing / Synced / Sync Error) at all times.

### 5.3 Mandi Clerk / Quality Inspector
- FR18: View a live checked-in queue with farmer, crop, token, allocated weight, and arrival window.
- FR19: Run AI crop quality inspection on an uploaded sample image.
- FR20: Manually override the AI-suggested grade.
- FR21: Enter official weighbridge weight.
- FR22: Accept or reject the crop, with a single primary action **"Accept Crop & Fulfill Delivery"** that atomically: marks procurement complete, stores official weight, finalizes quality record, increments PACS stock, generates an electronic receipt, and moves the farmer to `PAYMENT_DISPATCHED`.
- FR23: Reject flow updates farmer status to `REJECTED` with a reason and recommendation.

### 5.4 District Admin / DOCA
- FR24: Real-time counters: total farmers, today's bookings, checked-in, completed, pending, rejected, total quantity procured.
- FR25: Per-center PACS cards with storage utilization bars, color-coded Safe/Warning/Critical.
- FR26: Auto-generated evacuation alerts when a center crosses the Warning threshold (≥80%).
- FR27: Auto-lock of new bookings/token issuance when a center reaches Critical (≥95%), with nearest-center rerouting suggestion (search radius 15 km).
- FR28: "System Intelligence" panel with live cards: Queue Intelligence, Storage Intelligence, Equity Engine, AI Quality Inspection, Offline Sync, Logistics Automation.
- FR29: Queue/congestion visualization across centers.

---

## 6. Core Business Rules & Algorithms

### 6.1 Crop Weight Estimation
`Estimated Weight (Q) = Land Area (acres) × Crop Multiplier`

| Category | Crop | Q/Acre |
|---|---|---|
| Pulses | Tur | 8 |
| Pulses | Chana | 8 |
| Pulses | Masoor | 7 |
| Pulses | Moong | 6.5 |
| Pulses | Urad | 6.5 |
| Grains | Wheat | 18 |
| Grains | Paddy | 20 |
| Grains | Maize | 16 |
| Grains | Bajra | 12 |
| Grains | Jowar | 10 |

A ±15% tolerance is applied against the actual weighbridge reading before flagging a mismatch.

### 6.2 Social Equity Engine (must be backend-enforced, not just displayed)
- **Small farmer** = land area ≤ 5 acres.
- **40% reservation:** at least 40% of each center's daily procurement volume is reserved for small farmers; large-farmer bookings are blocked from consuming this reserved share.
- **50-quintal daily cap:** any single booking above 50 Q is automatically split into sequential dated tranches (e.g., 120 Q → 50 Q Day 1, 50 Q Day 4, 20 Q Day 7), spaced according to center capacity.

### 6.3 Storage-Aware Procurement
```
S_fill = (Current Stock + Incoming Booked Stock) / Maximum Godown Capacity × 100
```
| S_fill | State | Behavior |
|---|---|---|
| < 80% | Safe | Normal booking |
| 80% – <95% | Warning | Booking continues with warning banner + auto-generated evacuation alert (e.g., recommend N trucks) |
| ≥ 95% | Critical | New bookings and token issuance locked; system finds and recommends nearest center within 15 km |

### 6.4 Dynamic Arrival Window / Queue Engine
2-hour arrival windows are computed from: allocated crop quantity, center processing capacity, weighbridge throughput, quality-inspection capacity, current queue depth, farmer's travel distance, available storage, and the small-farmer reservation. Goal: smooth arrivals across the day instead of mass simultaneous arrival.

### 6.5 AI Crop Quality Inspection (heuristic, clearly labeled non-laboratory)
Image-based pipeline (Pillow/OpenCV): validates the image, analyzes RGB/pixel distribution, detects dark/discolored kernels, and estimates moisture via a documented heuristic.

| Grade | Moisture | Outcome |
|---|---|---|
| A | < 14.5% | Excellent — ready for procurement |
| B | 14.5% – 16.5% | Warning — recommend 1 extra day of drying |
| Rejected | > 16.5% | High moisture — recommend drying before visiting mandi |

All results are labeled **"AI-assisted preliminary assessment"** — never presented as lab-accurate.

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Offline resilience | Guard and clerk core operations must function fully offline via IndexedDB + Service Worker, with guaranteed, deduplicated sync on reconnect |
| Accessibility | Hindi/English toggle; feature-phone/voice simulation for non-smartphone users; large touch targets, high contrast |
| Performance | Slot/queue calculations and storage checks must reflect near real-time state for admin dashboards |
| Data integrity | No duplicate bookings, no duplicate offline transaction processing, no negative/impossible quantities |
| Security | No plaintext password storage; input validation on every endpoint; secrets via environment variables only |
| Usability | Farmer flows must be completable by a low-literacy, low-connectivity user in a handful of taps or one voice call |
| Transparency | Every automated decision (rerouting, tranche split, rejection) must show the farmer/admin a clear, human-readable reason |

---

## 8. System Architecture (summary)

- **Frontend:** HTML5 + Tailwind CSS + vanilla JS, Web Speech API (Hindi voice), IndexedDB, Service Worker, QR generation.
- **Backend:** Python 3.11, FastAPI, Pydantic, Uvicorn, Pillow/OpenCV for image analysis.
- **Database:** PostgreSQL via Supabase — core tables: `users`, `procurement_centers`, `slots`, `quality_inspections`, `evacuation_alerts`, plus `payments`, `weighments`, `offline_transactions`, `notifications`, `procurement_receipts`, `center_daily_quotas`.
- **Engines (backend services):** `queue_engine.py` (arrival windows), `storage_engine.py` (S_fill + locking/rerouting), `quality_engine.py` (AI grading), `procurement_engine.py` (equity rules, tranching, status transitions).
- **Sync model:** offline-first client with a local `offline_queue`, reconciled via `POST /api/sync-offline-transactions` with idempotent transaction IDs.

*(Full API endpoint list, DB schema, and file-by-file implementation are covered in the accompanying technical build, not duplicated here.)*

---

## 9. Key User Flows (acceptance-level)

1. **Booking:** Farmer registers → selects crop/land → system computes weight → applies 50-Q cap (tranches if needed) → checks center storage → issues token with QR + arrival window, or reroutes if center is Critical.
2. **Gate entry (online & offline):** Guard scans token → verifies → checks in. If offline, transaction is queued locally and marked "Pending Sync"; on reconnect it syncs automatically and confirms "Synced Successfully."
3. **Quality & weighment:** Clerk sees farmer in live queue → runs AI inspection or overrides manually → enters weighbridge weight → clicks "Accept Crop & Fulfill Delivery" → procurement completes, stock updates, receipt generates, payment status advances.
4. **Admin monitoring:** Dashboard reflects new stock/storage %, procurement counts, and any newly triggered evacuation alerts immediately after each completed procurement.
5. **Voice/feature-phone demo:** Farmer "calls in," Hindi voice dialogue collects name/land/crop, system computes yield, issues token, simulates SMS.

---

## 10. Success Metrics (for hackathon demo evaluation)

| Metric | Target |
|---|---|
| End-to-end demo flow completion | All 9 demo steps run without manual data patching |
| Offline check-in → sync | 100% of queued transactions sync with zero duplicates |
| Equity enforcement | Small-farmer 40% share and 50-Q cap verifiably enforced in booking logic, not just UI copy |
| Storage lockout | Bookings at a ≥95% center are blocked and rerouted automatically |
| AI grading clarity | Every AI result visibly labeled as preliminary/non-laboratory |
| Judge-facing differentiators | All 9 differentiators (Section 24 of source spec) visibly surfaced in the UI |

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| AI moisture heuristic seen as inaccurate/misleading | Explicit "AI-assisted preliminary assessment" labeling everywhere it's shown |
| Offline sync conflicts/duplicates | Idempotent transaction IDs; server-side dedup check before applying |
| Equity rules bypassed via edge cases (e.g., exactly 5 acres, exactly 50 Q) | Boundary conditions explicitly unit-tested in `procurement_engine.py` |
| Storage race condition (two bookings push center over 95% simultaneously) | Recompute `S_fill` at booking-commit time, not just at page load |
| Demo fragility (live offline toggle) | Guard dashboard clearly surfaces connectivity + sync state at all times for visible demo confidence |

---

## 12. Open Questions
- Should tranche bookings for the same farmer be schedulable at *different* centers if the home center is full, or must all tranches stay at one center?
- What is the authoritative source of "processing capacity" and "weighbridge speed" per center for the queue engine — configured constants or historical throughput?
- Is payment status purely informational in this prototype, or should it drive any farmer-facing action (e.g., dispute flag)?

---

*This PRD accompanies the full technical specification (architecture, DB schema, API contracts, and source code) delivered separately as the working prototype build.*
