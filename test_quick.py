import os
from dotenv import load_dotenv
load_dotenv()

KEY = os.getenv('GEMINI_API_KEY')
MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
print(f"Key: {KEY[:10]}..." if KEY else "❌ NO KEY")
print(f"Model: {MODEL}")

# Test new library
print("\n--- Testing google.genai ---")
try:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=KEY)
    response = client.models.generate_content(
        model=MODEL,
        contents="Say hello in 5 words",
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=50,
        ),
    )
    print(f"✅ NEW LIB WORKS: {response.text}")
except Exception as e:
    print(f"❌ New lib failed: {type(e).__name__}: {e}")

    # Test old library
    print("\n--- Testing google.generativeai ---")
    try:
        import google.generativeai as genai_old
        genai_old.configure(api_key=KEY)
        model = genai_old.GenerativeModel(MODEL)
        response = model.generate_content("Say hello in 5 words")
        print(f"✅ OLD LIB WORKS: {response.text}")
    except Exception as e2:
        print(f"❌ Old lib also failed: {type(e2).__name__}: {e2}")

print("\nDone!")