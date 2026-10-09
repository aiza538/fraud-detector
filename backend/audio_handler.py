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
                "error": f"Audio could not be transcribed: {transcript.error}",
                "_source": "Transcription_Error",
            }

        transcribed_text = transcript.text
        print(f"✅ Transcribed Text: {transcribed_text}")
        
        if not transcribed_text or len(transcribed_text.strip()) < 2:
            return {
                "error": "No clear speech detected in the audio, so it could not be analyzed.",
                "_source": "Silent_Audio",
            }

        # Pass the text to our existing fraud detector
        result = analyze_text(transcribed_text)
        result["transcript"] = transcribed_text
        return result
        
    except Exception as e:
        print(f"Backend Audio Exception: {e}")
        return {
            "error": f"Server error while processing audio: {str(e)[:120]}",
            "_source": "Audio_Error",
        }