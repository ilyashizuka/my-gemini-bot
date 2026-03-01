import os
import google.generativeai as genai

def get_ai_answer(prompt):
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    
    # Disable filters to prevent Gemini from blocking responses in Russian
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key:
            print(f"LOG: Key {name} not found in environment variables", flush=True)
            continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Generation with security settings
            response = model.generate_content(prompt, safety_settings=safety_settings)
            
            if response and response.text:
                return response.text
            else:
                print(f"LOG: Key {name} returned an empty response", flush=True)
                
        except Exception as e:
            # NOW YOU WILL SEE THE ERROR IN RENDER LOGS
            print(f"KEY ERROR {name}: {e}", flush=True)
            if "User location is not supported" in str(e):
                return "Error: Google blocks Render (bad server region). Requires a proxy or changing the region in Render."
            continue

    return "❌ All keys checked, no response. Check Render logs!"
