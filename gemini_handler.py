import os
import sys
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# Чтобы логи в Render появлялись мгновенно
sys.stdout.reconfigure(line_buffering=True)

def get_ai_answer(prompt):
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    models_to_try = ['gemini-1.5-flash', 'gemini-2.0-flash']

    print(f"📡 ИИ: Начинаю поиск ответа на запрос...")

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key:
            print(f"❓ Переменная {name} не найдена в Render.")
            continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            print(f"🔑 Пробую ключ {name} (длина: {len(key)} симв.)...")
            
            genai.configure(api_key=key)
            
            for model_name in models_to_try:
                try:
                    print(f"🤖 Пробую модель {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    
                    response = model.generate_content(
                        prompt, 
                        request_options=RequestOptions(api_version='v1')
                    )
                    
                    if response and response.text:
                        print(f"✅ УСПЕХ: Ответ получен через {name} / {model_name}")
                        return response.text
                        
                except Exception as model_err:
                    print(f"⚠️ Ошибка модели {model_name}: {model_err}")
                    continue
                    
        except Exception as config_err:
            print(f"🔥 Ошибка конфигурации {name}: {config_err}")
            continue
            
    print("❌ ИТОГ: Ни один ключ или модель не сработали.")
    return "❌ Ошибка: Все ключи ИИ исчерпаны или недоступны."
