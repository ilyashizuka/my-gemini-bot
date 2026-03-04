import os
import sys
import google.generativeai as genai

# Чтобы логи в Render появлялись мгновенно
sys.stdout.reconfigure(line_buffering=True)

def get_ai_answer(prompt):
    # Твои три ключа из Render
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    
    # ИСПОЛЬЗУЕМ ПОЛНЫЕ ИМЕНА МОДЕЛЕЙ (это лечит ошибку 404 в логах)
    # Сначала проверенная 1.5, потом экспериментальные версии
    models_to_try = [
        'models/gemini-1.5-flash', 
        'models/gemini-1.5-pro', 
        'models/gemini-2.0-flash-exp'
    ]

    print(f"📡 ИИ: Начинаю поиск ответа на запрос...")

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key: 
            continue
            
        try:
            # Очистка ключа от возможных кавычек
            key = raw_key.strip().replace('"', '').replace("'", "")
            print(f"🔑 Пробую ключ {name}...")
            
            genai.configure(api_key=key)
            
            for model_name in models_to_try:
                try:
                    print(f"🤖 Пробую модель {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    
                    # Простой вызов генерации контента
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        print(f"✅ УСПЕХ: Ответ получен через {name} / {model_name}")
                        return response.text
                        
                except Exception as model_err:
                    err_str = str(model_err)
                    # Если лимит исчерпан (429) или модель не найдена (404)
                    if "429" in err_str:
                        print(f"⚠️ У ключа {name} стоит лимит 0 на модель {model_name}")
                    elif "404" in err_str:
                        print(f"⚠️ Модель {model_name} не найдена (404). Пробую следующую...")
                    else:
                        print(f"⚠️ Ошибка {model_name}: {err_str[:100]}...") 
                    continue
                    
        except Exception as config_err:
            print(f"🔥 Ошибка конфигурации ключа {name}: {config_err}")
            continue
            
    print("❌ ИТОГ: Ни один ключ или модель не сработали.")
    return "❌ Ошибка: ИИ не смог пробиться (лимиты или 404). Проверь логи Render."
