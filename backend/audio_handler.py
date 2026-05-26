import assemblyai as aai
from fraud_detector import analyze_text
from dotenv import load_dotenv
import os

load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

def analyze_audio(file_path: str):
    transcriber = aai.Transcriber()
    
    config = aai.TranscriptionConfig(
        language_detection=True  # auto detect Urdu/English
    )
    
    transcript = transcriber.transcribe(file_path, config=config)

    if transcript.status == aai.TranscriptStatus.error:
        return {
            "fraud": False,
            "type": "Error",
            "confidence": 0,
            "peca": "N/A",
            "attack": "None",
            "target": "N/A",
            "language": "Unknown",
            "tactics": [],
            "education": ["Audio could not be transcribed. Try a clearer recording."],
            "complaint": None,
            "transcript": None
        }

    transcribed_text = transcript.text
    result = analyze_text(transcribed_text)
    result["transcript"] = transcribed_text
    return result