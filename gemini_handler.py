import os
import google.generativeai as genai
import traceback # Добавили для вывода точной причины

def get_ai_answer(prompt):
    keys = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    
    for name in keys:
        key = os.environ.get(name)
        if not key: continue
        
        try:
            # Очистка ключа
            clean_key = key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=clean_key)
            
            # Пробуем модель
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            return response.text
            
        except Exception:
            # Если ошибка внутри цикла - пишем её в консоль Render
            print(f"Ошибка в ключе {name}: {traceback.format_exc()}")
            continue

    # Если всё упало, возвращаем ПОЛНЫЙ ТЕКСТ ошибки из последнего сбоя
    return f"КРИТИЧЕСКИЙ СБОЙ ФУНКЦИИ:\n{traceback.format_exc()}"
