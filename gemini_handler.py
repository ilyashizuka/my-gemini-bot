import os
import sys
import google.generativeai as genai

sys.stdout.reconfigure(line_buffering=True)

def get_ai_answer(prompt):
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    
    print("📡 AI: Starting deep search for available models...")

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key: continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            print(f"🔑 Trying key {name}...")
            genai.configure(api_key=key)
            
            # --- MAGIC: Auto-search for available models ---
            available_models = []
            try:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                print(f"🔎 Found available models for this key: {available_models}")
            except Exception as e:
                print(f"⚠️ Failed to get the list of models for {name}: {e}")
                # If no list is given, try the standard ones at random (without a prefix)
                available_models = ['gemini-1.5-flash', 'gemini-pro']

            for model_name in available_models:
                try:
                    # Skip old and heavy models if there are many
                    if 'vision' in model_name or 'ultra' in model_name: continue
                    
                    print(f"🤖 Trying model {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        print(f"✅ SUCCESS: Answer via {name} / {model_name}")
                        return response.text
                        
                except Exception as model_err:
                    print(f"⚠️ Error {model_name}: {str(model_err)[:50]}")
                    continue
                    
        except Exception as config_err:
            print(f"🔥 Configuration error {name}: {config_err}")
            continue
            
    return "❌ RESULT: Google has hidden all models. It's time to change the account or move."
