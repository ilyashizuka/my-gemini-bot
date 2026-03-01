import os
import google.generativeai as genai

def get_ai_answer(prompt):
    # Список ключей из настроек Render
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    
    # Список актуальных названий моделей (пробуем по очереди)
    # Убрали -exp, так как Google мог его отключить
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key:
            continue
            
        try:
            # Чистим ключ от лишних символов
            key = raw_key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=key)
            
            for model_name in models_to_try:
                try:
                    print(f"Пробую модель {model_name} с ключом {name}...", flush=True)
                    model = genai.GenerativeModel(model_name)
                    
                    # Пытаемся получить ответ
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        return response.text
                except Exception as model_err:
                    print(f"Модель {model_name} не ответила: {model_err}", flush=True)
                    continue # Пробуем следующую модель для этого же ключа
                
        except Exception as e:
            print(f"Критическая ошибка ключа {name}: {e}", flush=True)
            continue

    return "❌ Все модели (2.0 и 1.5) выдали ошибку. Скорее всего, регион Render заблокирован Google (403)."
