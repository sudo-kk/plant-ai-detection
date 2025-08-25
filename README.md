# Plant AI Disease Detection - Deployment Guide

A full-stack plant disease detection application with AI-powered analysis using Google Gemini.

## 🌐 Live Demo
- Frontend: [Your Cloudflare Pages URL]
- API: [Your Cloudflare Worker URL]

## 🚀 Quick Deploy

### Prerequisites
- Node.js 18+
- Cloudflare account
- Google Gemini API key

### 1. Deploy Backend (Cloudflare Worker)
```bash
cd worker
npm install
npx wrangler login
npx wrangler deploy
```

### 2. Set Environment Variables
In Cloudflare dashboard → Workers & Pages → your-worker → Settings → Variables:
```
GEMINI_API_KEY = your_google_gemini_api_key
```

### 3. Deploy Frontend (Cloudflare Pages)
1. Push to GitHub
2. Connect repository to Cloudflare Pages
3. Build settings:
   - Build command: `cd frontend && npm install && npm run build`
   - Build output directory: `frontend/dist`
   - Environment variables: `VITE_API_BASE=https://your-worker.workers.dev`

## 🛠️ Local Development

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

### Worker (Local Testing)
```bash
cd worker
npm install
npx wrangler dev
```

## 📁 Project Structure
```
custom-plantAI/
├── backend/          # FastAPI development server
├── frontend/         # React + Vite + Tailwind
├── worker/           # Cloudflare Worker (production API)
├── .gitignore
└── README.md
```

## 🔧 Environment Variables

### Frontend (.env.production)
```
VITE_API_BASE=https://your-worker.workers.dev
```

### Worker (Cloudflare Dashboard)
```
GEMINI_API_KEY=your_google_gemini_api_key
```

## 🎯 Features
- Drag-and-drop image upload
- AI-powered disease detection
- Real-time confidence scoring
- Treatment recommendations
- Mobile-responsive design
- Serverless deployment
