import os
import telebot
import asyncio
from telebot import types
# Импортируем твои функции из соседних файлов
from gemini_handler import get_ai_answer
from db_worker import run_parser
from botani4ka import get_formatted_text, load_knowledge
import sys; sys.stdout.reconfigure(line_buffering=True)

# 1. Настройки из Render
raw_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
BOT_TOKEN = raw_token.replace('"', '').replace("'", "")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

bot = telebot.TeleBot(BOT_TOKEN)

# Предварительная загрузка базы знаний (один раз при старте)
KNOWLEDGE = load_knowledge()

# Вспомогательная функция для синхронного запуска асинхронной "ботанички"
def sync_get_text(topic):
    try:
        return asyncio.run(get_formatted_text(topic))
    except Exception as e:
        print(f"❌ Ошибка сборки текста для {topic}: {e}")
        return "⚠️ Ошибка загрузки данных. Пожалуйста, попробуйте позже."

# --- БЛОК КЛАВИАТУР ---

# Постоянное НИЖНЕЕ меню (Reply Keyboard) - для Супергруппы
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

# Кнопки под описанием вариантов проживания (Inline)
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

# Кнопки для выбора маршрута (Inline)
def get_route_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚗 На машине", callback_data="ROUTE_AUTO"),
        types.InlineKeyboardButton("🚌 Автобус / Электричка", callback_data="ROUTE_PUBLIC")
    )
    return markup

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_messages(message):
    if not message.text:
        return

    msg_text = message.text.strip()
    msg_lower = msg_text.lower()

    # --- 1. ПРИВЕТСТВИЕ (Только Ботаничка и Кнопки) ---
    if msg_lower in ['/start', '/menu', 'меню']:
        bot.send_chat_action(message.chat.id, 'typing')
        welcome = (
            "<b>Привет! Я помощница Ботаничка.</b> 🌿\n\n"
            "Помогу сориентироваться на базе «Вуокса-Вирта».\n"
            "Выберите нужный раздел в меню под клавиатурой:"
        )
        bot.send_message(message.chat.id, welcome, reply_markup=get_main_reply_keyboard(), parse_mode='HTML')
        return

    # --- 2. ДОМА И ЦЕНЫ ---
    price_triggers = ["цены", "стоимость", "🏠 дома и цены", "проживание"]
    if any(word in msg_lower for word in price_triggers):
        bot.send_chat_action(message.chat.id, 'typing')
        answer = sync_get_text("ВАРИАНТЫ_ПРОЖИВАНИЯ")
        bot.send_message(message.chat.id, answer, reply_markup=get_houses_keyboard(), parse_mode='Markdown')
        return

    # --- 3. МАРШРУТ (С кнопками выбора транспорта) ---
    if any(word in msg_lower for word in ["маршрут", "доехать", "добраться", "📍"]):
        bot.send_chat_action(message.chat.id, 'typing')
        answer = sync_get_text("МАРШРУТ")
        bot.send_message(message.chat.id, answer, reply_markup=get_route_keyboard(), parse_mode='Markdown')
        return

    # --- 4. ВЫЗОВ GEMINI (/**) - ТОЛЬКО ДЛЯ АДМИНА ---
    if msg_text.startswith('/**'):
        if message.from_user.id == ADMIN_ID:
            query = msg_text[3:].strip()
            if query:
                bot.send_chat_action(message.chat.id, 'typing')
                answer = get_ai_answer(query)
                bot.reply_to(message, answer)
        return

    # --- 5. КОМАНДА /UPDATE (АДМИН) ---
    if msg_lower == '/update' and message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "⏳ Обновляю базу цен...")
        run_parser()
        bot.send_message(message.chat.id, "✅ База MySQL успешно обновлена!")
        return

    # --- 6. ОБРАБОТКА ТЕКСТОВЫХ КНОПОК НИЖНЕГО МЕНЮ ---
    if any(word in msg_lower for word in ["лодки", "прокат", "🚣‍♂️"]):
        bot.send_message(message.chat.id, sync_get_text("ЛОДКИ"), parse_mode='Markdown')
        return
    
    if any(word in msg_lower for word in ["сауна", "баня", "🔥"]):
        bot.send_message(message.chat.id, sync_get_text("БАНЯ_НА_ДРОВАХ"), parse_mode='Markdown')
        return
    
    if any(word in msg_lower for word in ["контакты", "📞", "телефон"]):
        bot.send_message(message.chat.id, sync_get_text("КОНТАКТЫ"), parse_mode='Markdown')
        return

    # --- 7. УМНЫЙ ПОИСК ПО KNOWLEDGE.TXT (Остальные ключи) ---
    for full_key in KNOWLEDGE.keys():
        keywords = [k.strip().lower() for k in full_key.split(',')]
        if any(word in msg_lower for word in keywords if len(word) > 2):
            bot.send_chat_action(message.chat.id, 'typing')
            answer = sync_get_text(full_key)
            bot.send_message(message.chat.id, answer, parse_mode='Markdown', disable_web_page_preview=False)
            return

# --- ОБРАБОТЧИКИ НАЖАТИЙ (CALLBACK) ---

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data.startswith("HOUSE_"):
        topic = call.data.replace("HOUSE_", "")
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown')
    
    elif call.data.startswith("ROUTE_"):
        topic = "МАРШРУТ_АВТО" if call.data == "ROUTE_AUTO" else "МАРШРУТ_ОБЩЕСТВЕННЫЙ"
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    try:
        # 1. Принудительно удаляем вебхуки и старые соединения
        bot.remove_webhook()
        # 2. Маленькая пауза, чтобы Telegram успел закрыть старую сессию
        import time
        time.sleep(2) 
        
        print("✅ Ботаничка в сети и готова приветствовать гостей!")
        # 3. Запускаем с интервалом проверки (interval), это тоже снижает риск 409
        bot.infinity_polling(timeout=30, long_polling_timeout=5, interval=1)
    except Exception as e:
        print(f"🔥 Критическая ошибка запуска: {e}")
