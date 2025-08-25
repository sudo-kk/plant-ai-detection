import io
import os
import time
import base64
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import httpx
from dotenv import load_dotenv

APP_TITLE = "PlantAI Backend"
APP_VERSION = "0.1.0"

# Environment config
# Load .env if present
load_dotenv()
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent")
MAX_IMAGE_MB = float(os.getenv("MAX_IMAGE_MB", "8"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app = FastAPI(title=APP_TITLE, version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"]
    ,allow_headers=["*"]
)

class PredictResponse(BaseModel):
    id: str
    disease: str
    confidence: float
    suggestions: List[str]
    inference_ms: int

class ErrorResponse(BaseModel):
    detail: str

@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}

async def call_gemini(api_key: str, image_bytes: bytes) -> dict:
    # Encode image to base64 for Gemini content API
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    url = GEMINI_API_URL.format(model=GEMINI_MODEL)
    # Google Generative Language API expects API key via query param `key`
    params = {"key": api_key}
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": """Analyze this plant image for diseases. Respond in this exact JSON format:
{
  "disease_name": "specific disease name or 'Healthy'",
  "confidence": 0.85,
  "analysis": "detailed explanation of symptoms observed",
  "recommendations": ["specific actionable advice", "treatment steps"]
}

Be precise about confidence (0.0-1.0) based on clarity of symptoms. If unclear, use lower confidence."""
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "topK": 1,
            "topP": 0.8,
            "maxOutputTokens": 1000
        }
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, params=params, json=payload)
        r.raise_for_status()
        return r.json()


def simple_heuristic(image: Image.Image) -> tuple[str, float, List[str]]:
    # Enhanced heuristic with multiple factors for realistic confidence
    img = image.convert("RGB").resize((128, 128))
    pixels = list(img.getdata())
    
    if not pixels:
        return ("Unknown", 0.0, ["Retake photo in better light."])
    
    total = len(pixels)
    
    # Color analysis
    greens = sum(1 for r,g,b in pixels if g > r+10 and g > b+10 and g > 80)
    browns = sum(1 for r,g,b in pixels if r > g+5 and r > b+5 and r > 100)
    yellows = sum(1 for r,g,b in pixels if r > 150 and g > 150 and b < 100)
    blacks = sum(1 for r,g,b in pixels if r < 50 and g < 50 and b < 50)
    
    # Brightness and contrast analysis
    brightness_vals = [0.299*r + 0.587*g + 0.114*b for r,g,b in pixels]
    avg_brightness = sum(brightness_vals) / total
    brightness_std = (sum((b - avg_brightness)**2 for b in brightness_vals) / total) ** 0.5
    
    # Edge detection simulation (contrast between adjacent pixels)
    edge_count = 0
    for i in range(0, len(pixels)-129, 128):  # Row by row
        for j in range(127):  # Adjacent pixels in row
            if abs(sum(pixels[i+j]) - sum(pixels[i+j+1])) > 100:
                edge_count += 1
    
    edge_density = edge_count / (127 * (total // 128)) if total >= 128 else 0
    
    # Calculate ratios
    green_ratio = greens / total
    brown_ratio = browns / total
    yellow_ratio = yellows / total
    black_ratio = blacks / total
    
    # Decision logic with confidence based on multiple factors
    if green_ratio > 0.4 and brown_ratio < 0.1 and yellow_ratio < 0.05:
        # Healthy plant indicators
        confidence = min(0.85, 0.6 + green_ratio * 0.3 + (brightness_std / 50) * 0.1)
        return ("Healthy", confidence, ["Continue current care routine", "Monitor for changes"])
    
    elif yellow_ratio > 0.15 or (yellow_ratio > 0.08 and brown_ratio > 0.05):
        # Yellowing suggests nutrient deficiency or disease
        confidence = min(0.82, 0.5 + yellow_ratio * 1.5 + brown_ratio * 0.8)
        return ("Leaf Yellowing (Nutrient Deficiency)", confidence, 
                ["Check nitrogen levels", "Improve drainage", "Reduce watering frequency"])
    
    elif brown_ratio > 0.2 or black_ratio > 0.1:
        # Brown/black spots suggest fungal issues
        confidence = min(0.78, 0.45 + brown_ratio * 1.2 + black_ratio * 1.5)
        return ("Fungal Leaf Spot", confidence, 
                ["Remove affected leaves", "Improve air circulation", "Apply fungicide if severe"])
    
    elif edge_density > 0.3 and brightness_std > 40:
        # High contrast/edges might indicate pest damage or disease patterns
        confidence = min(0.65, 0.4 + edge_density * 0.5)
        return ("Possible Pest Damage", confidence, 
                ["Inspect for insects", "Check undersides of leaves", "Consider organic pesticide"])
    
    elif avg_brightness < 80:
        # Very dark image
        confidence = 0.25
        return ("Poor Image Quality", confidence, 
                ["Retake in better lighting", "Ensure leaf is clearly visible"])
    
    else:
        # Uncertain case
        confidence = 0.35 + green_ratio * 0.2
        return ("Early Stage Stress", confidence, 
                ["Monitor closely", "Check watering schedule", "Ensure adequate light"])

@app.post("/predict", response_model=PredictResponse, responses={400: {"model": ErrorResponse}})
async def predict(
    image: UploadFile = File(...),
    x_gemini_api_key: Optional[str] = Header(default=None, convert_underscores=False)
):
    # Validate image
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPEG or PNG.")

    content = await image.read()
    size_mb = len(content) / (1024*1024)
    if size_mb > MAX_IMAGE_MB:
        raise HTTPException(status_code=413, detail=f"Image too large. Max {MAX_IMAGE_MB} MB")

    # Load PIL image
    try:
        pil = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    t0 = time.time()
    disease = "Unknown"
    conf = 0.0
    tips: List[str] = []

    # Prefer header key; fall back to env key
    api_key = x_gemini_api_key or os.getenv(GEMINI_API_KEY_ENV)

    if api_key:
        try:
            data = await call_gemini(api_key, content)
            # Parse Gemini response for structured JSON output
            text = ""
            if isinstance(data, dict):
                candidates = data.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for p in parts:
                        if "text" in p:
                            text += p["text"]
            
            if text:
                try:
                    # Try to extract JSON from response
                    import json
                    import re
                    
                    # Look for JSON in the response
                    json_match = re.search(r'\{[^{}]*"disease_name"[^{}]*\}', text, re.DOTALL)
                    if json_match:
                        gemini_result = json.loads(json_match.group())
                        disease = gemini_result.get("disease_name", "Unknown Disease")[:80]
                        conf = float(gemini_result.get("confidence", 0.7))
                        conf = max(0.1, min(0.95, conf))  # Clamp between 0.1-0.95
                        
                        analysis = gemini_result.get("analysis", "")
                        recommendations = gemini_result.get("recommendations", [])
                        
                        tips = []
                        if analysis:
                            tips.append(f"Analysis: {analysis[:200]}")
                        if recommendations:
                            tips.extend(recommendations[:3])  # Limit to 3 recommendations
                        
                        if not tips:
                            tips = ["AI analysis completed", "Consult plant expert for severe cases"]
                            
                    else:
                        # Fallback: parse free-form text
                        lines = text.strip().split('\n')
                        disease = lines[0][:80] if lines else "Disease Detected"
                        conf = 0.7  # Default for unstructured response
                        tips = [line.strip() for line in lines[1:4] if line.strip()] or ["AI analysis provided"]
                        
                except (json.JSONDecodeError, KeyError, ValueError):
                    # If JSON parsing fails, use basic text parsing
                    lines = text.strip().split('\n')
                    disease = lines[0][:80] if lines else "Disease Analysis"
                    conf = 0.6  # Lower confidence for unparsed response
                    tips = [line.strip() for line in lines[1:3] if line.strip()] or ["Review AI response"]
            else:
                disease, conf, tips = simple_heuristic(pil)
        except httpx.HTTPStatusError as e:
            # If auth or other API error, fall back
            disease, conf, tips = simple_heuristic(pil)
        except Exception:
            disease, conf, tips = simple_heuristic(pil)
    else:
        disease, conf, tips = simple_heuristic(pil)

    t_ms = int((time.time()-t0)*1000)
    return PredictResponse(
        id=str(int(time.time()*1000)),
        disease=disease,
        confidence=round(conf,3),
        suggestions=tips,
        inference_ms=t_ms
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
