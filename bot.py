import os
import telebot
import asyncio
from telebot import types
from gemini_handler import get_ai_answer
from db_worker import run_parser
from botani4ka import get_formatted_text, load_knowledge

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip().replace('"', '')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

bot = telebot.TeleBot(BOT_TOKEN)
KNOWLEDGE = load_knowledge()

def sync_get_text(topic):
    try:
        return asyncio.run(get_formatted_text(topic))
    except Exception as e:
        print(f"Ошибка: {e}")
        return "⚠️ Ошибка данных"

# КЛАВИАТУРЫ
def get_houses_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_5 = types.InlineKeyboardButton("🏠 Пятёрочка", callback_data="HOUSE_ПЯТЕРОЧКА")
    btn_srub = types.InlineKeyboardButton("🌲 Сруб с баней", callback_data="HOUSE_СРУБ")
    btn_kom = types.InlineKeyboardButton("🏢 Коммуналка", callback_data="HOUSE_КОММУНАЛКА")
    btn_std = types.InlineKeyboardButton("🎱 Студия", callback_data="HOUSE_СТУДИЯ")
    btn_bg = types.InlineKeyboardButton("⛺️ Бунгало", callback_data="HOUSE_БУНГАЛО")
    markup.add(btn_5, btn_srub)
    markup.add(btn_kom, btn_std)
    markup.add(btn_bg)
    return markup

def get_route_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_car = types.InlineKeyboardButton("🚗 На машине", callback_data="ROUTE_AUTO")
    btn_public = types.InlineKeyboardButton("🚌 Автобус / Электричка", callback_data="ROUTE_PUBLIC")
    markup.add(btn_car, btn_public)
    return markup

# ОБРАБОТЧИК СООБЩЕНИЙ
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_messages(message):
    if not message.text: return
    msg_lower = message.text.strip().lower()

    # Триггеры для главного меню
    menu_words = ["цены", "стоимость", "варианты", "проживани", "размещен", "какие дома"]
    if msg_lower == '/start' or any(w in msg_lower for w in menu_words):
        bot.send_chat_action(message.chat.id, 'typing')
        answer = sync_get_text("ВАРИАНТЫ_ПРОЖИВАНИЯ")
        bot.send_message(message.chat.id, answer, reply_markup=get_houses_keyboard(), parse_mode='Markdown')
        return

    # Триггер для лодок
    if any(w in msg_lower for w in ["лодки", "прокат", "весла", "мотор"]):
        bot.send_message(message.chat.id, sync_get_text("ЛОДКИ"), parse_mode='Markdown')
        return

    # Умный поиск по остальным ключам
    for key in KNOWLEDGE.keys():
        keywords = [k.strip().lower() for k in key.split(',')]
        if any(word in msg_lower for word in keywords if len(word) > 2):
            if any(r in keywords for r in ["маршрут", "доехать", "добраться"]):
                bot.send_message(message.chat.id, sync_get_text(key), reply_markup=get_route_keyboard(), parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, sync_get_text(key), parse_mode='Markdown', disable_web_page_preview=False)
            return

# ОБРАБОТЧИКИ КНОПОК
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data.startswith("HOUSE_"):
        topic = call.data.replace("HOUSE_", "")
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown')
    
    elif call.data.startswith("ROUTE_"):
        topic = "МАРШРУТ_АВТО" if call.data == "ROUTE_AUTO" else "МАРШРУТ_ОБЩЕСТВЕННЫЙ"
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown')
    
    # Оживляем кнопки
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    bot.remove_webhook()
    print("🚀 Бот запущен!")
    bot.infinity_polling(timeout=30)
