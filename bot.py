import os
import telebot
import time
from gemini_handler import get_ai_answer 

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("CRITICAL ERROR: Token not found!", flush=True)
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    print(f"User wrote: {message.text}", flush=True) # Check incoming
    try:
        # Send "typing" status so the user sees activity
        bot.send_chat_action(message.chat.id, 'typing')
        
        ai_response = get_ai_answer(message.text)
        
        print(f"AI response received (first 20 chars): {ai_response[:20]}", flush=True)
        bot.send_message(message.chat.id, ai_response)
    except Exception as e:
        print(f"ERROR IN BOT.PY: {e}", flush=True)
        bot.send_message(message.chat.id, "The bot encountered an error. See logs.")

if __name__ == "__main__":
    print("--- ЧИСТКА ХВОСТОВ (409) ---", flush=True)
    try:
        # 1. Сносим вебхук на корню
        bot.remove_webhook()
        
        # 2. Пауза 5 секунд, чтобы Telegram понял: мы свободны
        import time
        time.sleep(5) 
        
        print("Запускаю поллинг...", flush=True)
        # 3. Игнорируем старые сообщения (чтобы бот не спамил при старте)
        bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)
    except Exception as e:
        print(f"Ошибка при старте: {e}", flush=True)
