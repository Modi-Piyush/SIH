# Smart Storage-Aware Farmer Procurement & Offline-Resilient Supply Chain Platform
### SIH Problem Statement PS26032

An end-to-end digital procurement platform designed for Primary Agricultural Credit Societies (PACS) and state procurement agencies. The platform eliminates mandi congestion, enforces 40% smallholder reservation quotas, provides AI-assisted multi-parameter crop quality grading, offers dynamic storage-aware routing with predictive evacuation, and features a zero-loss offline synchronization engine.

---

## 🌟 Key Features

1. **Social Equity & Smallholder Tranche Engine**:
   - Automatic land-holding classification (Small/Marginal $\le 5$ acres vs Large $> 5$ acres).
   - Strict 40% daily PACS capacity reservation for small and marginal farmers.
   - Large harvest split into multi-date tranches (max 100 quintals per booking) to prevent capacity monopolization.

2. **Real-Time Storage Admission & Evacuation Engine**:
   - Dynamic fill-rate monitoring ($S_{\text{fill}} = \frac{\text{Current Stock} + \text{Incoming Booked}}{\text{Max Capacity}} \times 100$).
   - Automatic traffic light state management: `GREEN` ($<80\%$), `WARNING` ($80-94\%$), `CRITICAL_LOCK` ($\ge 95\%$).
   - Predictive evacuation dispatch: calculates excess quintals, recommended truck counts (100 Q capacity each), and routing to nearest buffer depots.

3. **Multi-Parameter AI Crop Quality Inspection**:
   - Computer Vision pre-screening analyzing moisture discoloration, foreign matter, and broken kernels.
   - Instant classification into Grade A, Grade B, or Rejected with confidence scoring and manual override audit trails.

4. **Offline-Resilient Gate Sync (Local-First IndexedDB)**:
   - Complete offline functionality for PACS entry gates using Client-Side IndexedDB and Service Workers.
   - Idempotent UUID-based transaction replay with SHA-256 integrity verification upon reconnection.

5. **Multilingual Interactive Voice Assistant**:
   - Hindi and English voice simulation allowing farmers to query centers, check estimated yields, and book slots by voice.

6. **Interactive Role Dashboards**:
   - **Farmer Portal**: Slot booking, digital token QR generation, pre-screening, notifications, and payment tracking.
   - **Gate Guard Terminal**: Token verification, check-in, offline manifest caching.
   - **PACS Clerk Desk**: Queue processing, weighbridge tolerance validation ($\pm 5\%$), payment calculation, and receipt generation.
   - **Admin Command Center**: Real-time storage intelligence, capacity gauges, evacuation dispatching, and system metrics.

---

## 🏗️ Tech Stack

- **Backend**: Python 3.10+ / FastAPI, Pydantic v2, Uvicorn
- **Database**: SQLite (Supabase/PostgreSQL compatible schema)
- **Computer Vision / AI**: Pillow (PIL) Image Analysis & Color Space Matrix Inspection
- **Frontend**: Vanilla HTML5, CSS3 (Modern Glassmorphism Design System), JavaScript (ES6+), Chart.js, HTML5-QRCode, IndexedDB API
- **Deployment**: Vercel Serverless Python Runtime

---

## 🚀 Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Modi-Piyush/farmer-procurement-platform.git
cd farmer-procurement-platform
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Access the Application
- **Web App**: [http://localhost:8000](http://localhost:8000)
- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Redoc API**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Automated Tests

Run the full suite of unit and integration tests:
```bash
python -m unittest discover tests
```

---

## ☁️ Deploying to Vercel

### Option 1: Automatic Deployment via GitHub (Recommended)
1. Push this repository to your GitHub account:
   ```bash
   git remote add origin https://github.com/Modi-Piyush/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```
2. Go to [vercel.com/new](https://vercel.com/new).
3. Import your GitHub repository.
4. Click **Deploy**. Vercel will automatically detect `vercel.json` and Python dependencies from `requirements.txt`.

### Option 2: Deploy using Vercel CLI
```bash
npm install -g vercel
vercel
```

---

## 📁 Project Structure

```
.
├── api/
│   └── index.py               # Vercel serverless function entry point
├── app/
│   ├── main.py                # FastAPI app setup, CORS, static routes
│   ├── database.py            # SQLite schema, migrations, connection pool & demo seeder
│   ├── routers/
│   │   ├── farmer.py          # Farmer registration, bookings, pre-screening, tokens
│   │   ├── guard.py           # Guard check-in & offline manifests
│   │   ├── clerk.py           # Weighbridge validation, quality certification, payments
│   │   ├── admin.py           # Capacity metrics, storage intelligence, evacuation
│   │   └── voice.py           # Voice assistant NLP backend
│   └── services/
│       ├── procurement_engine.py  # Equity engine, tranche splitting, MSP calculations
│       ├── storage_engine.py      # Fill rates, state evaluator, nearest center routing
│       ├── quality_engine.py      # Computer Vision crop image analysis
│       └── queue_engine.py        # Arrival window allocation
├── static/
│   ├── index.html             # Single Page Application HTML
│   ├── css/
│   │   └── style.css          # Glassmorphism design system & responsive layout
│   ├── js/
│   │   ├── app.js             # Client application logic & UI controllers
│   │   └── offline.js         # IndexedDB storage & background sync engine
│   └── service-worker.js      # PWA offline asset caching
├── tests/
│   ├── test_api_endpoints.py  # FastAPI integration tests
│   └── test_engines.py        # Core algorithm unit tests
├── vercel.json                # Vercel serverless routing configuration
├── requirements.txt           # Python package dependencies
├── .vercelignore              # Files excluded from Vercel deployment
└── .gitignore                 # Files excluded from Git version control
```

---

## 📜 License

MIT License. Developed for Smart India Hackathon (SIH) Problem Statement PS26032.
