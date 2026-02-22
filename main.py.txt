import os
import google.generativeai as genai

# Берем ключ из настроек Render
api_key = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-pro')

if __name__ == "__main__":
    try:
        response = model.generate_content("Привет! Ты работаешь на сервере Render?")
        print("\n--- УСПЕХ! ОТВЕТ ОТ GEMINI ---")
        print(response.text)
        print("------------------------------\n")
    except Exception as e:
        print("Ошибка при запросе:", e)
