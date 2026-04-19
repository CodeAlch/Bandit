import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

print(f"API Key: {GEMINI_KEY[:10]}...{GEMINI_KEY[-5:]}" if GEMINI_KEY else "❌ NO API KEY!")
print(f"Model: {GEMINI_MODEL}")

import google.generativeai as genai
genai.configure(api_key=GEMINI_KEY)

model = genai.GenerativeModel(GEMINI_MODEL)

# Test 1: Simple chat
print("\n--- Test 1: Simple chat ---")
try:
    response = model.generate_content("Say hello in one sentence")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 2: JSON response
print("\n--- Test 2: JSON response ---")
try:
    response = model.generate_content(
        'Return ONLY this JSON, nothing else: {"message": "hello!", "actions": []}'
    )
    print(f"Raw: {response.text}")
    import json
    parsed = json.loads(response.text.strip().replace('```json','').replace('```',''))
    print(f"Parsed: {parsed}")
    print(f"Type: {type(parsed)}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 3: Complex instruction
print("\n--- Test 3: Bot-like instruction ---")
try:
    prompt = """You are a Discord bot. Return ONLY valid JSON.
User says: "who are you?"
Return: {"message": "your response", "actions": []}
JSON:"""
    response = model.generate_content(prompt)
    print(f"Raw: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n✅ All tests done!")