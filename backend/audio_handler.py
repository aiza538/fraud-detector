import assemblyai as aai
from fraud_detector import analyze_text
from dotenv import load_dotenv
import os

load_dotenv()

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

def analyze_audio(file_path: str):
    try:
        transcriber = aai.Transcriber()
        
        # We use the default model for maximum compatibility first
        config = aai.TranscriptionConfig(
            language_code="ur" # Tell it to expect Urdu
        )

        print(f"🎙️ Sending {file_path} to AssemblyAI...")
        transcript = transcriber.transcribe(file_path, config=config)

        if transcript.status == aai.TranscriptStatus.error:
            print(f"❌ AssemblyAI Error: {transcript.error}")
            return {
                "fraud": False,
                "type": "Transcription Error",
                "confidence": 0,
                "peca": "N/A",
                "attack": "None",
                "target": "N/A",
                "language": "Unknown",
                "tactics": [],
                "education": [f"Audio could not be transcribed: {transcript.error}"],
                "complaint": None,
                "transcript": None
            }

        transcribed_text = transcript.text
        print(f"✅ Transcribed Text: {transcribed_text}")
        
        if not transcribed_text or len(transcribed_text.strip()) < 2:
            return {
                "fraud": False,
                "type": "Silent/Unclear Audio",
                "education": ["We could not hear any clear speech in the audio."],
                # ... (fill in other defaults)
            }

        # Pass the text to our existing fraud detector
        result = analyze_text(transcribed_text)
        result["transcript"] = transcribed_text
        return result
        
    except Exception as e:
        print(f"Backend Audio Exception: {e}")
        return {
                "fraud": False,
                "type": "Processing Error",
                "education": [f"Server error while processing audio: {e}"]
                # ...
        }