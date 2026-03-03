import os
import telebot
import asyncio
from gemini_handler import get_ai_answer
from db_worker import run_parser
from botani4ka import get_formatted_text, load_knowledge

# Загрузка настроек
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip().replace('"', '')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

bot = telebot.TeleBot(BOT_TOKEN)
KNOWLEDGE = load_knowledge()

def sync_get_text(topic):
    try:
        return asyncio.run(get_formatted_text(topic))
    except Exception as e:
        return f"⚠️ Ошибка: {e}"

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    if not message.text: return
    msg_text = message.text.strip()
    msg_lower = msg_text.lower()

    if msg_lower == '/start':
        bot.reply_to(message, sync_get_text("ВАРИАНТЫ_ПРОЖИВАНИЯ"), parse_mode='Markdown')
        return

    if msg_lower == '/update' and message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "⏳ Обновляю базу...")
        result = run_parser()
        bot.send_message(message.chat.id, "✅ Готово!")
        return

    for key in KNOWLEDGE.keys():
        if key.lower() in msg_lower:
            bot.send_message(message.chat.id, sync_get_text(key), parse_mode='Markdown')
            return

if __name__ == "__main__":
    bot.remove_webhook()
    bot.infinity_polling()
