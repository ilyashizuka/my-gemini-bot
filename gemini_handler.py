import os
import google.generativeai as genai
from google.generativeai.types import RequestOptions

def get_ai_answer(prompt):
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash']

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key: 
            continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=key)
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt, 
                        request_options=RequestOptions(api_version='v1')
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    print(f"⚠️ Ошибка модели {model_name} на ключе {name}: {e}")
                    continue
        except Exception as e:
            print(f"🔥 Ошибка конфигурации ключа {name}: {e}")
            continue
            
    return "❌ Ошибка: Все ключи ИИ исчерпаны или недоступны."
