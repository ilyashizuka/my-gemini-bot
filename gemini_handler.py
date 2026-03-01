import os
import google.generativeai as genai

def get_ai_answer(prompt):
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    
    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key:
            continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Генерация контента
            response = model.generate_content(prompt)
            
            # ЖЕСТКАЯ ПРОВЕРКА: если Gemini вернул пустой объект или заблокировал ответ
            if response and hasattr(response, 'text') and response.text:
                return response.text
            else:
                continue # Пробуем следующий ключ, если этот выдал пустоту
                
        except Exception:
            continue

    # Если прошли все ключи и везде пустота/ошибки
    return "Извини, ИИ не смог сформировать ответ. Проверь ключи в Render."
