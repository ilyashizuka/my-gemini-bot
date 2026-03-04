import os
import telebot
import asyncio
from telebot import types
# Импортируем функции из соседних файлов
from gemini_handler import get_ai_answer
from db_worker import run_parser
from botani4ka import get_formatted_text, load_knowledge

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

# Постоянное НИЖНЕЕ меню (Reply Keyboard)
def get_main_reply_keyboard():
    # Добавили input_field_placeholder — это текст внутри поля ввода, 
    # он часто помогает "проявить" кнопки в интерфейсе групп
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, 
        row_width=2, 
        selective=False,
        input_field_placeholder="Выберите нужный раздел..."
    )
    btn_houses = types.KeyboardButton("🏠 Дома и цены")
    btn_boats = types.KeyboardButton("🚣‍♂️ Прокат лодок")
    btn_route = types.KeyboardButton("📍 Маршрут")
    btn_sauna = types.KeyboardButton("🔥 Сауна")
    btn_contacts = types.KeyboardButton("📞 Контакты")
    
    markup.add(btn_houses, btn_boats)
    markup.add(btn_route, btn_sauna)
    markup.add(btn_contacts)
    return markup

# Кнопки под описанием вариантов проживания (Inline)
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

# Кнопки для выбора маршрута (Inline)
def get_route_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_car = types.InlineKeyboardButton("🚗 На машине", callback_data="ROUTE_AUTO")
    btn_public = types.InlineKeyboardButton("🚌 Автобус / Электричка", callback_data="ROUTE_PUBLIC")
    markup.add(btn_car, btn_public)
    return markup

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_messages(message):
    if not message.text:
        return

    msg_text = message.text.strip()
    msg_lower = msg_text.lower()

    # --- КОМАНДЫ /START и /MENU (Приветствие + нижнее меню) ---
    if msg_lower in ['/start', '/menu']:
        bot.send_chat_action(message.chat.id, 'typing')
        welcome_text = (
            "<b>Добро пожаловать на базу «Вуокса-Вирта»!</b> 🌿\n\n"
            "Я ваш цифровой помощник. Используйте кнопки меню ниже, "
            "чтобы узнать цены, маршрут или правила проживания."
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_reply_keyboard(), parse_mode='HTML')
        return

    # --- ГЛАВНОЕ МЕНЮ (Только когда нажали кнопку или написали "цены") ---
    main_menu_triggers = ["цены", "стоимость", "варианты", "проживани", "размещен", "какие дома", "дома и цены"]
    if any(word in msg_lower for word in main_menu_triggers):
        bot.send_chat_action(message.chat.id, 'typing')
        answer = sync_get_text("ВАРИАНТЫ_ПРОЖИВАНИЯ")
        # Выводим общий прайс + Inline кнопки конкретных домов
        bot.send_message(message.chat.id, answer, reply_markup=get_houses_keyboard(), parse_mode='Markdown')
        return

    # --- КОМАНДА /UPDATE (АДМИН) ---
    if msg_lower == '/update' and message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "⏳ Обновляю базу цен с сайта...")
        result = run_parser()
        bot.send_message(message.chat.id, "✅ База успешно обновлена!")
        return

    # --- ВЫЗОВ GEMINI (/**) - ТОЛЬКО ДЛЯ АДМИНА ---
    if msg_text.startswith('/**'):
        if message.from_user.id == ADMIN_ID:
            query = msg_text[3:].strip()
            if query:
                bot.send_chat_action(message.chat.id, 'typing')
                answer = get_ai_answer(query)
                bot.reply_to(message, answer)
        else:
            bot.reply_to(message, "🤫 Эта команда доступна только администратору.")
        return

    # --- УМНЫЙ ПОИСК ПО KNOWLEDGE.TXT ---
    # Поиск по лодкам
    if any(word in msg_lower for word in ["лодки", "прокат лодок", "весла", "мотор"]):
        bot.send_message(message.chat.id, sync_get_text("ЛОДКИ"), parse_mode='Markdown')
        return

    # Поиск по всем остальным блокам
    for full_key in KNOWLEDGE.keys():
        keywords = [k.strip().lower() for k in full_key.split(',')]
        if any(word in msg_lower for word in keywords if len(word) > 2):
            bot.send_chat_action(message.chat.id, 'typing')
            
            if any(r in keywords for r in ["маршрут", "доехать", "добраться"]):
                answer = sync_get_text(full_key)
                bot.send_message(message.chat.id, answer, reply_markup=get_route_keyboard(), parse_mode='Markdown')
            else:
                answer = sync_get_text(full_key)
                bot.send_message(message.chat.id, answer, parse_mode='Markdown', disable_web_page_preview=False)
            return

# --- ОБРАБОТЧИКИ НАЖАТИЙ (CALLBACK) ---

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data.startswith("HOUSE_"):
        topic = call.data.replace("HOUSE_", "")
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown', disable_web_page_preview=False)
    
    elif call.data.startswith("ROUTE_"):
        topic = "МАРШРУТ_АВТО" if call.data == "ROUTE_AUTO" else "МАРШРУТ_ОБЩЕСТВЕННЫЙ"
        bot.send_message(call.message.chat.id, sync_get_text(topic), parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        print("🚀 Бот запущен! ИИ под замком, меню на базе.")
        bot.infinity_polling(timeout=30)
    except Exception as e:
        print(f"🔥 Ошибка: {e}")
