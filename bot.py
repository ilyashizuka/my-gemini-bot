import os
import telebot
import asyncio
from telebot import types # Добавили для кнопок
from gemini_handler import get_ai_answer
from db_worker import run_parser
from botani4ka import get_formatted_text, load_knowledge

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip().replace('"', '')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

bot = telebot.TeleBot(BOT_TOKEN)
KNOWLEDGE = load_knowledge()

def sync_get_text(topic):
    try:
        # Прямой запуск асинхронной функции
        return asyncio.run(get_formatted_text(topic))
    except Exception as e:
        print(f"Ошибка сборки текста: {e}")
        return "⚠️ Ошибка данных"

# Функция создания кнопок для Маршрута
def get_route_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_car = types.InlineKeyboardButton("🚗 На машине", callback_data="ROUTE_AUTO")
    btn_bus = types.InlineKeyboardButton("🚌 Автобус/Электричка", callback_data="ROUTE_PUBLIC")
    markup.add(btn_car, btn_bus)
    return markup

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    if not message.text: return
    msg_text = message.text.strip().lower()

    # --- МАРШРУТ (с живыми кнопками) ---
    if "маршрут" in msg_lower or "доехать" in msg_lower:
        text = sync_get_text("МАРШРУТ")
        bot.send_message(message.chat.id, text, reply_markup=get_route_keyboard(), parse_mode='Markdown')
        return

    # --- ПЯТЁРОЧКА И ОСТАЛЬНЫЕ ---
    for key in KNOWLEDGE.keys():
        if key.lower() in msg_lower:
            text = sync_get_text(key)
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
            return

# Обработка нажатий на кнопки маршрута
@bot.callback_query_handler(func=lambda call: call.data.startswith("ROUTE_"))
def callback_route(call):
    topic = "МАРШРУТ_АВТО" if call.data == "ROUTE_AUTO" else "МАРШРУТ_ОБЩЕСТВЕННЫЙ"
    text = sync_get_text(topic)
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    bot.remove_webhook()
    bot.infinity_polling()
