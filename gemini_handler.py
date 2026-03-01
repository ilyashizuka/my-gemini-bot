import os
import google.generativeai as genai

def get_ai_answer(prompt):
    # Список твоих ключей из Render
    KEY_NAMES = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    errors = []

    for name in KEY_NAMES:
        key = os.environ.get(name)
        if not key:
            errors.append(f"{name}: отсутствует в Render")
            continue

        try:
            # Чистим ключ от всякого мусора
            clean_key = key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=clean_key)
            
            # Пробуем именно Flash 2.0
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            if response and response.text:
                return response.text
                
        except Exception as e:
            # Сохраняем текст ошибки, чтобы показать его тебе
            errors.append(f"{name}: {str(e)}")
            continue

    # Если всё сдохло, бот пришлет тебе список всех ошибок
    return "ОШИБКИ КЛЮЧЕЙ:\n" + "\n".join(errors)
