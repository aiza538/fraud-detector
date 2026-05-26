from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fraud_detector import analyze_text
from audio_handler import analyze_audio
import shutil, os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextRequest(BaseModel):
    text: str

# Tab 1 — Paste Text
@app.post("/analyze")
async def analyze(req: TextRequest):
    return analyze_text(req.text)

# Tab 2 — Upload File (.txt)
@app.post("/analyze-file")
async def analyze_file(file: UploadFile = File(...)):
    contents = await file.read()
    text = contents.decode("utf-8")
    return analyze_text(text)

# Tab 3 — Upload Audio
@app.post("/analyze-audio")
async def analyze_audio_endpoint(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    result = analyze_audio(temp_path)
    os.remove(temp_path)
    return result

@app.get("/health")
async def health():
    return {"status": "running"}