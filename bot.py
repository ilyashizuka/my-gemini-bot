import os
import telebot
import time
import sys
import codecs
from gemini_handler import get_ai_answer
from db_worker import save_to_db

# Принудительно ставим UTF-8 для логов Render, чтобы не было кракозябр
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("CRITICAL ERROR: Token not found!", flush=True)
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- 1. КОМАНДА UPDATE (БЕЗ ИИ) ---
@bot.message_handler(commands=['update'])
def run_update(message):
    print(f"--- ЗАПУСК ПАРСЕРА (БЕЗ ИИ) от {message.from_user.id} ---", flush=True)
    try:
        bot.reply_to(message, "⏳ Синхронизация с БД Hostland: очистка и запись...")
        
        # Вызываем функцию из db_worker.py
        success = save_to_db(
            url="manual_tg_call", 
            title=f"Запуск от {message.from_user.first_name}", 
            price="0", 
            phone="---", 
            content="Ручное обновление базы через Telegram-бота"
        )
        
        if success:
            bot.send_message(message.chat.id, "✅ Старые данные удалены. Новая запись в parsed_content добавлена!")
        else:
            bot.send_message(message.chat.id, "❌ Ошибка БД. Проверь логи Render или белый список IP в Hostland.")
            
    except Exception as e:
        print(f"ОШИБКА В ХЕНДЛЕРЕ UPDATE: {e}", flush=True)
        bot.send_message(message.chat.id, f"❌ Критический сбой: {e}")

# --- 2. ОБЫЧНЫЕ СООБЩЕНИЯ (С ИИ) ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    print(f"Запрос к ИИ: {message.text}", flush=True)
    try:
        # Статус "печатает"
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Запрос к Джемени
        ai_response = get_ai_answer(message.text)
        
        print(f"Ответ ИИ получен (первые 20 симв): {ai_response[:20]}", flush=True)
        bot.send_message(message.chat.id, ai_response)
    except Exception as e:
        print(f"ОШИБКА ИИ: {e}", flush=True)
        bot.send_message(message.chat.id, "Бот столкнулся с ошибкой при обращении к ИИ.")

if __name__ == "__main__":
    print("--- СТАРТ БОТА (ЧИСТКА 409) ---", flush=True)
    try:
        bot.remove_webhook()
        time.sleep(5) 
        print("Запускаю поллинг...", flush=True)
        bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)
    except Exception as e:
        print(f"Ошибка старта: {e}", flush=True)
