import os
import google.generativeai as genai

def get_ai_answer(prompt):
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    
    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key: continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=key)
            
            # Тот самый Флэш 2.0, который работал неделю назад
            # Если выдаст 404, значит Google убрал приставку -exp
            model_name = 'gemini-2.0-flash-exp' 
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            if response and response.text:
                return response.text
                
        except Exception as e:
            print(f"ОШИБКА {name} (модель {model_name}): {e}", flush=True)
            # Если 2.0 сдохла, пробуем старую добрую 1.5 в этом же цикле
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                if response.text: return response.text
            except:
                continue
            continue

    return "❌ Все модели (2.0 и 1.5) выдали 404 или 403. Проверь регион Render."
