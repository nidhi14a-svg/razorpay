# RAZZZ: AI Campaign Intelligence & Decision Engine

## What It Does
RAZZZ is an AI-powered revenue optimization platform for merchants.
Merchant sets a goal → AI analyzes historical data & creates personalized campaign → Deterministic Backend validates against merchant rules → Tracks real-time results & provides optimization actions.

## Core Features
1. **Customer Segmentation:** Rule-based identification of customer behavior (e.g., loyal, new_visitor, cart_abandoned).
2. **AI-Powered Personalization:** Generates context-aware offers strictly guided by merchant rules and historical performance.
3. **Deterministic Guardrails:** AI recommendations are validated against strict margin and discount limits.
4. **Historical Learning Loop:** Campaign results continuously feed back into the AI to improve future accuracy.
5. **Campaign Intelligence:** Summarizes large-scale campaign data into actionable insights for the merchant.

## Tech Stack
- Backend: Python FastAPI, PyMongo, Pydantic
- Frontend: Next.js (React, TailwindCSS)
- Database: MongoDB
- AI: OpenRouter (Claude/OpenAI via standard interface)
- Payments: Razorpay (Test Mode)

## Quick Start

### 1. Environment Variables
Create a `.env` file in the `backend/` directory:
```env
# MongoDB Connection String (Atlas or Local)
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/smart_segmentation

# OpenRouter API Key (AI agent interactions)
OPENROUTER_API_KEY=your_openrouter_api_key

# Razorpay Test Credentials (for payment verification)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt

# Create initial demo merchant and customers
python demo.py

# Run the API
uvicorn main:app --reload
```
Backend runs at: http://localhost:8000

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at: http://localhost:3000

## Testing
The backend features an extensive Pytest suite for end-to-end functionality.
```bash
cd backend
python -m pytest -v
```