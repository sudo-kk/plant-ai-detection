# PlantAI Backend (FastAPI)

Endpoints
- GET /health – health check
- POST /predict – multipart form with `image` (JPEG/PNG). Optional header `X-Gemini-Api-Key` to use Google Gemini for AI recognition. If not provided, falls back to a simple heuristic.

Config
- Environment variables:
  - GEMINI_API_KEY – default API key (optional; can be overridden per request via header)
  - GEMINI_MODEL – default `gemini-1.5-flash`
  - GEMINI_API_URL – default `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  - ALLOWED_ORIGINS – CORS origins (comma-separated). Default `*`.
  - MAX_IMAGE_MB – default `8`

Quick start (Windows PowerShell)
1. Create venv and install deps
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run dev server
```
$env:GEMINI_API_KEY="YOUR_KEY_HERE"; uvicorn app:app --reload --port 8000
```

3. Test health
```
Invoke-RestMethod -Uri http://localhost:8000/health
```

4. Test predict

PowerShell (multipart form):
```
$file = Get-Item .\sample.jpg
Invoke-RestMethod `
  -Uri http://localhost:8000/predict `
  -Method Post `
  -Headers @{ 'X-Gemini-Api-Key' = 'YOUR_KEY' } `
  -Form @{ image = $file }
```

curl:
```
curl -X POST http://localhost:8000/predict \
  -H "X-Gemini-Api-Key: YOUR_KEY" \
  -F image=@sample.jpg
```

Notes
- If you don’t set a Gemini key, the endpoint returns a heuristic guess.
- The Gemini output is parsed simply; refine parsing as needed.
