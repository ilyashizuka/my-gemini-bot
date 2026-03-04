import os
import telebot
import asyncio
from telebot import types
from gemini_handler import get_ai_answer
from db_worker import run_parser
from botani4ka import get_formatted_text, load_knowledge

# 1. Настройки
raw_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
BOT_TOKEN = raw_token.replace('"', '').replace("'", "")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

bot = telebot.TeleBot(BOT_TOKEN)
KNOWLEDGE = load_knowledge()

def sync_get_text(topic):
    try:
        return asyncio.run(get_formatted_text(topic))
    except Exception as e:
        print(f"❌ Ошибка данных: {e}")
        return "⚠️ Не удалось загрузить информацию."

# --- КЛАВИАТУРЫ ---

def get_main_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, selective=False)
    markup.add(
        types.KeyboardButton("🏠 Дома и цены"),
        types.KeyboardButton("🚣‍♂️ Прокат лодок"),
        types.KeyboardButton("📍 Маршрут"),
        types.KeyboardButton("🔥 Сауна"),
        types.KeyboardButton("📞 Контакты")
    )
    return markup

def get_houses_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🏠 Пятёрочка", callback_data="HOUSE_ПЯТЕРОЧКА"),
        types.InlineKeyboardButton("🌲 Сруб", callback_data="HOUSE_СРУБ"),
        types.InlineKeyboardButton("🏢 Коммуналка", callback_data="HOUSE_КОММУНАЛКА"),
        types.InlineKeyboardButton("🎱 Студия", callback_data="HOUSE_СТУДИЯ"),
        types.InlineKeyboardButton("⛺️ Бунгало", callback_data="HOUSE_БУНГАЛО")
    )
    return markup

def get_route_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Эти callback_data ДОЛЖНЫ совпадать с логикой в обработчике ниже
    btn_car = types.InlineKeyboardButton("🚗 На машине", callback_data="ROUTE_AUTO")
    btn_public = types.InlineKeyboardButton("🚌 Автобус / Электричка", callback_data="ROUTE_PUBLIC")
    markup.add(btn_car, btn_public)
    return markup

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_messages(message):
    if not message.text: return
    msg_text = message.text.strip()
    msg_lower = msg_text.lower()

    # --- КОМАНДЫ /START и /MENU ---
    if msg_lower in ['/start', '/menu', 'меню']:
        welcome = "<b>🌿 База «Вуокса-Вирта»</b>\nИспользуйте меню под клавиатурой для навигации:"
        bot.send_message(message.chat.id, welcome, reply_markup=get_main_reply_keyboard(), parse_mode='HTML')
        return

    # --- ДОМА И ЦЕНЫ ---
    if any(word in msg_lower for word in ["цены", "стоимость", "варианты", "🏠 дома и цены"]):
        answer = sync_get_text("ВАРИАНТЫ_ПРОЖИВАНИЯ")
        bot.send_message(message.chat.id, answer, reply_markup=get_houses_keyboard(), parse_mode='Markdown')
        return

    # --- МАРШРУТ (Главный триггер с кнопками выбора) ---
    if any(word in msg_lower for word in ["маршрут", "доехать", "добраться", "📍"]):
        answer = sync_get_text("МАРШРУТ")
        bot.send_message(message.chat.id, answer, reply_markup=get_route_keyboard(), parse_mode='Markdown')
        return

    # --- ЛОДКИ, САУНА, КОНТАКТЫ ---
    if any(word in msg_lower for word in ["лодки", "прокат", "🚣‍♂️"]):
        bot.send_message(message.chat.id, sync_get_text("ЛОДКИ"), parse_mode='Markdown')
        return
    if any(word in msg_lower for word in ["сауна", "баня", "🔥"]):
        bot.send_message(message.chat.id, sync_get_text("БАНЯ_НА_ДРОВАХ"), parse_mode='Markdown')
        return
    if any(word in msg_lower for word in ["контакты", "📞", "телефон"]):
        bot.send_message(message.chat.id, sync_get_text("КОНТАКТЫ"), parse_mode='Markdown')
        return

    # --- ИИ (Только Админ) ---
    if msg_text.startswith('/**') and message.from_user.id == ADMIN_ID:
        query = msg_text[3:].strip()
        if query: bot.reply_to(message, get_ai_answer(query))
        return

    # --- ОБНОВЛЕНИЕ БАЗЫ (Админ) ---
    if msg_lower == '/update' and message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "⏳ Обновляю...")
        run_parser()
        bot.send_message(message.chat.id, "✅ Цены обновлены!")
        return

    # --- УМНЫЙ ПОИСК ПО ФАЙЛУ (Для всего остального) ---
    for key in KNOWLEDGE.keys():
        keywords = [k.strip().lower() for k in key.split(',')]
        if any(word in msg_lower for word in keywords if len(word) > 2):
            bot.send_message(message.chat.id, sync_get_text(key), parse_mode='Markdown')
            return

# --- ОБРАБОТЧИКИ НАЖАТИЙ (CALLBACK) ---

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Выбор дома
    if call.data.startswith("HOUSE_"):
        topic = call.data.replace("HOUSE_", "")
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown')
    
    # Выбор маршрута (ТЕ САМЫЕ КНОПКИ)
    elif call.data.startswith("ROUTE_"):
        # Если нажали "На машине" -> ищем МАРШРУТ_АВТО в файле
        topic = "МАРШРУТ_АВТО" if call.data == "ROUTE_AUTO" else "МАРШРУТ_ОБЩЕСТВЕННЫЙ"
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    bot.remove_webhook()
    bot.infinity_polling(timeout=30)
