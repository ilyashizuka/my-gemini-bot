import os
import google.generativeai as genai

# Собираем все ключи в список
# В Render добавь переменные: GEMINI_KEY_1, GEMINI_KEY_2, GEMINI_KEY_3
KEYS = [
    os.environ.get('GEMINI_KEY_1'),
    os.environ.get('GEMINI_KEY_2'),
    os.environ.get('GEMINI_KEY_3')
]

def get_ai_answer(prompt):
    for key in KEYS:
        if not key: continue # Пропускаем, если ключ не задан
        
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            if "429" in str(e):
                print(f"Лимит ключа исчерпан, пробую следующий...")
                continue # Переходим к следующему ключу в цикле
            return f"Ошибка Gemini: {e}"
            
    return "Все ключи Gemini исчерпали лимиты. Попробуйте позже."
