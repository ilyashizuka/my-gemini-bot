import os
import google.generativeai as genai

# Список ключей из секретов Render
GEMINI_KEYS = [
    os.environ.get('GEMINI_KEY_1'),
    os.environ.get('GEMINI_KEY_2'),
    os.environ.get('GEMINI_KEY_3')
]

def get_ai_answer(prompt):
    for key in GEMINI_KEYS:
        if not key:
            continue
        
        try:
            genai.configure(api_key=key)
            # Используем твою любимую модель 2.0 Flash
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            # Если поймали лимит (429), пробуем следующий ключ
            if "429" in str(e):
                print(f"Ключ исчерпан, перехожу к следующему...")
                continue
            return f"Произошла ошибка: {e}"
            
    return "Извините, все доступные ключи ИИ сейчас перегружены."

