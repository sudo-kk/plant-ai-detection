# PlantAI Frontend (Vite + React + Tailwind)

- Clean, minimal UI to upload an image, enter Gemini API key, and view prediction.
- Stores API key in browser localStorage; sent as `X-Gemini-Api-Key` header.
- Configurable backend base URL via env.

Dev scripts (PowerShell)
```
npm install
npm run dev
```

Env
- Create `.env` with: `VITE_API_BASE=http://localhost:8000`
