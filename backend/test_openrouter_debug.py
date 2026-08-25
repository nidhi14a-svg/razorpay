#!/usr/bin/env python
"""Debug OpenRouter API connectivity"""

from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
print(f"API Key configured: {bool(api_key)}")
print(f"API Key starts with: sk-or-v1-{api_key[-20:] if api_key else 'NOT SET'}")

if not api_key:
    print("ERROR: OPENROUTER_API_KEY not set in .env")
    exit(1)

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    print("✓ OpenRouter client created")
    print(f"OpenAI SDK version: {__import__('openai').__version__}")

    model_name = "openrouter/free"
    request_url = "https://openrouter.ai/api/v1/chat/completions"

    print("\nAttempting API call to:")
    print(request_url)
    print(f"Model: {model_name}")

    response = client.chat.completions.create(
        model=model_name,
        max_tokens=100,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello in one sentence."}
        ]
    )
    print(f"✓ API call successful!")
    print(f"Response: {response.choices[0].message.content}")

except Exception as e:
    print(f"\n✗ Request failed")
    print(f"Exception type: {type(e).__name__}")
    print(f"Exception message: {e}")
    print(f"Request URL used: https://openrouter.ai/api/v1/chat/completions")
    print(f"Model used: openai/gpt-oss-20b:free")
    print(f"OpenAI SDK version: {__import__('openai').__version__}")

    # Try to capture the full OpenRouter error body if present
    status_code = None
    response_body = None

    if hasattr(e, 'response') and e.response is not None:
        status_code = getattr(e.response, 'status_code', None)
        try:
            response_body = e.response.json()
        except Exception:
            try:
                response_body = e.response.text
            except Exception:
                response_body = str(e.response)

    print(f"HTTP status code: {status_code}")
    print("Complete response/error body from OpenRouter:")
    print(json.dumps(response_body, indent=2, ensure_ascii=False) if isinstance(response_body, (dict, list)) else str(response_body))

    import traceback
    traceback.print_exc()
