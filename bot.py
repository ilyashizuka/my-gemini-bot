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
        print(f"❌ Ошибка: {e}")
        return "⚠️ Ошибка загрузки данных."

# --- БЛОК КЛАВИАТУР ---

# Та самая нижняя панель, которая будет видна во всех темах
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

# Инлайн-кнопки для выбора домика
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

# --- ОБРАБОТЧИКИ ---

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_messages(message):
    if not message.text: return
    msg_text = message.text.strip()
    msg_lower = msg_text.lower()

    # 1. Вызов главного меню (по команде или кнопке)
    main_triggers = ["/start", "/menu", "меню", "варианты", "🏠 дома и цены", "цены"]
    if any(word in msg_lower for word in main_triggers):
        bot.send_chat_action(message.chat.id, 'typing')
        answer = sync_get_text("ВАРИАНТЫ_ПРОЖИВАНИЯ")
        # Отправляем сообщение С НИЖНИМ МЕНЮ (оно приклеится к теме)
        bot.send_message(message.chat.id, answer, reply_markup=get_main_reply_keyboard(), parse_mode='Markdown')
        # И сразу Инлайн-кнопки домов
        bot.send_message(message.chat.id, "Выберите дом для деталей:", reply_markup=get_houses_keyboard())
        return

    # 2. Ограничение ИИ (Gemini) только для тебя
    if msg_text.startswith('/**'):
        if message.from_user.id == ADMIN_ID:
            query = msg_text[3:].strip()
            if query: bot.reply_to(message, get_ai_answer(query))
        return

    # 3. Обновление базы (Админ)
    if msg_lower == '/update' and message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "⏳ Обновляю цены...")
        run_parser()
        bot.send_message(message.chat.id, "✅ База MySQL обновлена!")
        return

    # 4. Обработка кнопок нижнего меню (Лодки, Сауна, Контакты)
    if "прокат лодок" in msg_lower:
        bot.send_message(message.chat.id, sync_get_text("ЛОДКИ"), parse_mode='Markdown')
        return
    if "🔥 сауна" in msg_lower or "баня" in msg_lower:
        bot.send_message(message.chat.id, sync_get_text("БАНЯ_НА_ДРОВАХ"), parse_mode='Markdown')
        return
    if "маршрут" in msg_lower:
        bot.send_message(message.chat.id, sync_get_text("МАРШРУТ"), parse_mode='Markdown')
        return
    if "контакты" in msg_lower:
        bot.send_message(message.chat.id, sync_get_text("КОНТАКТЫ"), parse_mode='Markdown')
        return

    # 5. Общий поиск по файлу (на всякий случай)
    for key in KNOWLEDGE.keys():
        keywords = [k.strip().lower() for k in key.split(',')]
        if any(word in msg_lower for word in keywords if len(word) > 2):
            bot.send_message(message.chat.id, sync_get_text(key), parse_mode='Markdown')
            return

# --- ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК (ВЫБОР ДОМА) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data.startswith("HOUSE_"):
        topic = call.data.replace("HOUSE_", "")
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown')
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        print("✅ Бот запущен! Кнопки нижнего меню готовы к работе в темах.")
        bot.infinity_polling(timeout=30)
    except Exception as e:
        print(f"🔥 Ошибка: {e}")
