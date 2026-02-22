import os
import telebot
import google.generativeai as genai

# Ключи
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# Настройка
genai.configure(api_key=GOOGLE_API_KEY)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Пробуем самую современную модель
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(message.text)
        
        bot.reply_to(message, response.text if response.text else "Пустой ответ")
        
    except Exception as e:
        # Если ошибка, выводим её и список доступных моделей
        error_msg = str(e)
        if "404" in error_msg:
            try:
                models = [m.name for m in genai.list_models()]
                available = "\n".join(models[:5]) # первые 5 моделей
                bot.reply_to(message, f"Ошибка 404. Доступные модели на сервере:\n{available}")
            except:
                bot.reply_to(message, f"Ошибка: {error_msg}")
        else:
            bot.reply_to(message, f"Ошибка: {error_msg}")

print("Бот запущен!")
bot.infinity_polling()
