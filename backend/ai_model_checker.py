import os
from google import genai
from dotenv import load_dotenv

# Load your .env file
load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_KEY:
    print("❌ API Key not found. Make sure .env is in the same folder.")
    exit()

client = genai.Client(api_key=GEMINI_KEY)

print("🔍 Querying Google AI Studio for available models...\n")

try:
    # List all models available to your specific API key
    models = client.models.list()
    
    print("✅ Models you can use for Text/Audio Analysis (generateContent):")
    for m in models:
        # We only care about models that can generate text/content
        if "generateContent" in m.supported_actions:
             print(f"  - {m.name}  (Display: {m.display_name})")
             
    print("\n💡 TIP: Copy one of the names from the list above (e.g., 'gemini-1.5-flash' or 'gemini-2.5-flash')")
    print("   and paste it into the 'model=' parameter in your fraud_detector.py file.")

except Exception as e:
    print(f"❌ Error fetching models: {e}")