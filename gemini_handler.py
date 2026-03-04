import os
import sys
import google.generativeai as genai

# Мгновенные логи
sys.stdout.reconfigure(line_buffering=True)

def get_ai_answer(prompt):
    # Твоя система перебора ключей и моделей
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    models_to_try = ['gemini-1.5-flash', 'gemini-2.0-flash']

    print(f"📡 ИИ: Начинаю поиск ответа на запрос...")

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key:
            print(f"❓ Переменная {name} не найдена.")
            continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            print(f"🔑 Пробую ключ {name}...")
            
            genai.configure(api_key=key)
            
            for model_name in models_to_try:
                try:
                    print(f"🤖 Пробую модель {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    
                    # Убрали RequestOptions(api_version='v1'), чтобы не было конфликта
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        print(f"✅ УСПЕХ: Ответ получен через {name} / {model_name}")
                        return response.text
                        
                except Exception as model_err:
                    print(f"⚠️ Ошибка модели {model_name}: {model_err}")
                    continue
                    
        except Exception as config_err:
            print(f"🔥 Ошибка конфигурации {name}: {config_err}")
            continue
            
    print("❌ ИТОГ: Все варианты перебраны, ответа нет.")
    return "❌ Ошибка: ИИ не смог пробиться. Проверь логи Render."
