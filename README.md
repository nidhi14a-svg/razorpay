# Smart Segmentation AI Revenue Agent

## What It Does
Merchant sets a goal → AI creates personalized campaign → Tracks results

## Tech Stack
- Backend: Python FastAPI
- Frontend: Next.js (JavaScript, not TypeScript)
- Database: MongoDB
- AI: Claude API
- Payments: Razorpay

## Quick Start

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```
Backend runs at: http://localhost:8000

### Frontend Setup (Day 2)
```bash
cd frontend
npx create-next-app@latest . --javascript --tailwind
npm run dev
```
Frontend runs at: http://localhost:3000