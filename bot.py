import os
import telebot
# Импортируем функцию из нашего отдельного модуля
from gemini_handler import get_ai_answer 

# Достаем токен из переменных окружения Render
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("КРИТИЧЕСКАЯ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN не найдена в Render!")
    exit(1)

# Инициализируем бота
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """
    ЭТАП 1: Получаем текст от пользователя, 
    отправляем его в gemini_handler и возвращаем ответ ИИ.
    """
    try:
        # Запрашиваем ответ у модуля Gemini (там внутри перебор 3-х ключей)
        ai_response = get_ai_answer(message.text)
        
        # Отправляем ответ пользователю в Telegram
        bot.send_message(message.chat.id, ai_response)
    except Exception as e:
        print(f"Ошибка при обработке сообщения: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при обращении к ИИ.")

if __name__ == "__main__":
    print("--- ЖЕСТКИЙ ПЕРЕЗАПУСК ---")
    try:
        # 1. Сначала полностью удаляем вебхук (чистим хвосты)
        bot.remove_webhook()
        import time
        time.sleep(2) # Даем Telegram 2 секунды, чтобы закрыть старое соединение
        
        print("Запускаю infinity_polling...")
        # 2. Используем infinity_polling с коротким таймаутом
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Ошибка при старте: {e}")
