import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai_service import extract_knowledge_map

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    text: str
    api_key: str | None = None


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "server_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
    }


@app.post("/api/extract")
def extract(req: ExtractRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")
    try:
        knowledge_map = extract_knowledge_map(req.text, api_key=req.api_key)
        return {"knowledge_map": knowledge_map}
    except ValueError as err:
        raise HTTPException(status_code=401, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


# Serve the frontend locally. Vercel handles static files itself and sets VERCEL=1.
if not os.environ.get("VERCEL"):
    app.mount("/", StaticFiles(directory=".", html=True), name="static")
