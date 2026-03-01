import os
import google.generativeai as genai

# Список имен твоих переменных из Render
KEY_NAMES = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']

def get_ai_answer(prompt):
    # Начало цикла перебора
    for name in KEY_NAMES:
        key = os.environ.get(name)
        
        if not key:
            print(f"[-] Пропуск: переменная {name} не найдена в Render")
            continue

        try:
            # Чистим ключ от мусора (пробелы, кавычки)
            clean_key = key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=clean_key)
            
            # Попытка запроса к Gemini 2.0 Flash
            print(f"[>] Пробую получить ответ через {name}...")
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            # Если дошли сюда — ключ сработал!
            print(f"[+] Успех! Ответ получен через {name}")
            return response.text

        except Exception as e:
            # Если ошибка — пишем её в лог и идем к следующему ключу
            print(f"[!] Ошибка ключа {name}: {e}")
            continue # ПЕРЕХОД К СЛЕДУЮЩЕМУ КЛЮЧУ В СПИСКЕ

    # Если цикл кончился, а return не сработал
    return "Все три ключа (1, 2, 3) выдали ошибку. Проверь логи Render."
