import os
import google.generativeai as genai
from google.generativeai.types import RequestOptions

def get_ai_answer(prompt):
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    
    # Пробуем эти модели. Если вылетает 404, библиотека сама подставит v1 вместо v1beta
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash']

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key: continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            
            # Настройка API
            genai.configure(api_key=key)
            
            for model_name in models_to_try:
                try:
                    print(f"Пробую {model_name} (ключ {name})...", flush=True)
                    model = genai.GenerativeModel(model_name)
                    
                    # ГЛАВНОЕ ИЗМЕНЕНИЕ: принудительно просим версию v1, чтобы не было 404
                    response = model.generate_content(
                        prompt,
                        request_options=RequestOptions(api_version='v1')
                    )
                    
                    if response and response.text:
                        return response.text
                except Exception as model_err:
                    print(f"Ошибка модели {model_name}: {model_err}", flush=True)
                    continue 
                
        except Exception as e:
            print(f"Ошибка ключа {name}: {e}", flush=True)
            continue

    return "❌ Все ключи выдали 404 или 403. Проверь регион сервера Render."
