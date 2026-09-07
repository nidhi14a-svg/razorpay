# RAZZZ: AI Campaign Intelligence & Revenue Agent

RAZZZ is an autonomous AI-powered revenue optimization and campaign decision engine for e-commerce merchants.

```
Merchant Onboarding → Guardrails Setup → Relational CSV Upload → Behavioral Metrics & Segmentation → AI Campaign Strategy → Decision Engine & Guardrail Audit → Execution & Performance Learning Loop
```

---

## Architecture Overview

- **Backend**: FastAPI (Python 3.10+) asynchronous REST API with streaming CSV processing, deterministic customer segmentation, and mathematical guardrail validation.
- **Frontend**: Next.js 16 (React 19, TailwindCSS, Lucide Icons) with server/client components, dark/light theme support, and responsive dashboards.
- **Database**: MongoDB (Atlas or Local) storing merchants, partitioned customer cohorts, campaigns, personalized offers, optimization tasks, and audit logs.
- **AI Agent**: OpenRouter (Claude / GPT models) generating evidence-based revenue strategies with automated deterministic fallback.
- **Payments & Coupons**: Razorpay SDK integration for discount voucher creation, customer checkout links, and webhook/polling payment verification.

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `MONGODB_URI` | MongoDB connection string (Local or MongoDB Atlas) | `mongodb+srv://user:pass@cluster.mongodb.net/smart_segmentation?retryWrites=true&w=majority` |
| `DB_NAME` | Target database name | `smart_segmentation` |
| `PORT` | FastAPI server listening port | `8000` |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | `http://localhost:3000,http://127.0.0.1:3000` |
| `FRONTEND_URL` | Public frontend URL for email verification and password reset links | `http://localhost:3000` |
| `OPENROUTER_API_KEY` | API Key for OpenRouter AI recommendation engine | `sk-or-v1-...` |
| `RAZORPAY_KEY_ID` | Razorpay Merchant Key ID | `rzp_test_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay Merchant Key Secret | `...` |
| `REQUIRE_EMAIL_VERIFICATION` | Enforce email confirmation before login (`true`/`false`) | `false` |
| `MAX_CSV_FILE_SIZE_MB` | Maximum allowed size per uploaded CSV in megabytes | `50` |
| `SMTP_SERVER` | SMTP host for outgoing notification emails | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USERNAME` | SMTP account username | `your-email@gmail.com` |
| `SMTP_PASSWORD` | SMTP app password | `xxxx xxxx xxxx xxxx` |
| `SENDER_EMAIL` | From address for outgoing emails | `your-email@gmail.com` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Public base URL of the FastAPI backend service | `http://localhost:8000` (Production: `https://api.yourdomain.com`) |

---

## Local Development Setup

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12
- Node.js 18.x or 20.x and npm
- MongoDB Community Server (or free MongoDB Atlas cluster)

### 2. Clone and Configure Environment Files
```bash
git clone https://github.com/nidhi14a-svg/razorpay.git razzz
cd razzz

# Setup backend environment file
cp backend/.env.example backend/.env

# Setup frontend environment file
cp frontend/.env.example frontend/.env.local
```

### 3. Backend Setup
```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv

# Windows PowerShell:
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# Install production dependencies
pip install -r requirements.txt

# (Optional) Seed demo merchant & customers:
python demo.py

# Start the development server
python main.py
# Or with uvicorn directly:
uvicorn main:app --reload --port 8000
```
Backend API will be live at: `http://localhost:8000`  
Swagger API Docs available at: `http://localhost:8000/docs`

### 4. Frontend Setup
In a new terminal:
```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
Frontend Web App will be live at: `http://localhost:3000`

---

## Production Deployment Guide

### A. Database (MongoDB Atlas)
1. Log into [MongoDB Atlas](https://cloud.mongodb.com/) and create a free M0 cluster or dedicated instance.
2. In **Database Access**, create a user with read/write permissions for database `smart_segmentation`.
3. In **Network Access**, add an IP Access List entry:
   - For cloud platforms with dynamic IPs (Render, Railway, Fly.io), add `0.0.0.0/0` (Allow access from anywhere) and secure via username/password.
4. Obtain your connection string:
   `mongodb+srv://<username>:<password>@<cluster>.mongodb.net/smart_segmentation?retryWrites=true&w=majority`
5. Set `MONGODB_URI` in your backend deployment environment variables. Database collections and indexes are automatically created on startup; no manual database migration is required.

### B. Backend Deployment (Render / Railway / Fly.io / Docker)

#### Option 1: Docker Container Deployment
A production `backend/Dockerfile` is included.
```bash
cd backend
docker build -t razzz-backend:latest .
docker run -p 8000:8000 --env-file .env razzz-backend:latest
```

#### Option 2: Render.com / Railway
1. Connect your GitHub repository.
2. Set Root Directory to `backend`.
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `python main.py` (or `uvicorn main:app --host 0.0.0.0 --port $PORT`)
5. Configure Environment Variables:
   - `MONGODB_URI`: `<Your MongoDB Atlas URI>`
   - `CORS_ORIGINS`: `https://your-frontend.vercel.app`
   - `FRONTEND_URL`: `https://your-frontend.vercel.app`
   - `OPENROUTER_API_KEY`: `<Your Key>`
   - `RAZORPAY_KEY_ID`: `<Your Key>`
   - `RAZORPAY_KEY_SECRET`: `<Your Secret>`
   - `REQUIRE_EMAIL_VERIFICATION`: `false`

### C. Frontend Deployment (Vercel / Netlify)
1. Import your GitHub repository into [Vercel](https://vercel.com).
2. Set Root Directory to `frontend`.
3. Framework Preset: `Next.js`.
4. Configure Environment Variables:
   - `NEXT_PUBLIC_API_URL`: `https://your-backend-service.onrender.com`
5. Click **Deploy**. Vercel will build and deploy the Next.js production bundle.

### D. Ephemeral Storage Note
The CSV upload system does not store uploaded files on disk. Datasets are parsed directly in-memory via streaming buffers and immediately ingested into MongoDB in partitioned batches. This design is fully compatible with serverless, containerized, and ephemeral environments (such as Vercel, Render, AWS ECS, and Heroku).

---

## Verification & Testing

Run the automated backend test pipeline:
```bash
cd backend
python test_multi_csv_pipeline.py
```
This tests:
- Relational joins across `customers`, `orders`, and `order_items` datasets
- Non-zero metric calculations (LTV, AOV, purchase counts, days since last purchase)
- Strict merchant isolation in MongoDB
- Rejection and error reporting for missing join keys
- AI Strategy generation with deterministic guardrail enforcement
- Diagnostic reporting for `NO_CUSTOMER_DATA` and `INSUFFICIENT_BEHAVIORAL_DATA` states