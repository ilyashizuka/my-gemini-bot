import os
import telebot
from gemini_handler import get_ai_answer
from db_worker import run_parser

# Чистим токен от возможных кавычек и пробелов из Render
raw_token = os.environ.get('BOT_TOKEN', '')
BOT_TOKEN = raw_token.strip().replace('"', '').replace("'", "")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    if not message.text: return

    # Команда /update
    if message.text == '/update':
        if message.from_user.id == ADMIN_ID:
            bot.reply_to(message, "⏳ Начинаю парсинг...")
            res = run_parser()
            bot.send_message(message.chat.id, res)
        else:
            bot.reply_to(message, "🔐 Доступ запрещен.")
        return

    # Вызов Gemini через /**
    if message.text.startswith('/**'):
        query = message.text[3:].strip()
        if query:
            bot.send_chat_action(message.chat.id, 'typing')
            bot.reply_to(message, get_ai_answer(query))
        else:
            bot.reply_to(message, "Напиши вопрос после /**")

if __name__ == "__main__":
    print("🚀 Бот запущен...")
    bot.infinity_polling()
