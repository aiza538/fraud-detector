import assemblyai as aai
from fraud_detector import analyze_text
from dotenv import load_dotenv
import os

load_dotenv()

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

def analyze_audio(file_path: str):
    transcriber = aai.Transcriber()
    
    # ✅ New config — no language_detection, use universal-3-pro model
    config = aai.TranscriptionConfig(
        speech_model=aai.SpeechModel.universal,   # supports Urdu + English + Roman Urdu
        language_code="ur",                        # set to Urdu (handles Roman Urdu too)
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