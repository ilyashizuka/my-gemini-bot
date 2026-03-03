import os
import telebot
import asyncio
from telebot import types
# Импортируем твои функции из соседних файлов
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

# Функция создания кнопок для раздела Маршрут
def get_route_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_car = types.InlineKeyboardButton("🚗 На машине", callback_data="ROUTE_AUTO")
    btn_public = types.InlineKeyboardButton("🚌 Автобус / Электричка", callback_data="ROUTE_PUBLIC")
    markup.add(btn_car, btn_public)
    return markup

# 2. Обработчик всех входящих сообщений
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    if not message.text:
        return

    msg_text = message.text.strip()
    msg_lower = msg_text.lower()

    # --- КОМАНДА /START ---
    if msg_lower == '/start':
        bot.send_chat_action(message.chat.id, 'typing')
        # Выводим главный блок вариантов проживания
        answer = sync_get_text("ВАРИАНТЫ_ПРОЖИВАНИЯ")
        bot.reply_to(message, answer, parse_mode='Markdown')
        return

    # --- КОМАНДА /UPDATE (АДМИН) ---
    if msg_lower == '/update':
        if message.from_user.id == ADMIN_ID:
            bot.reply_to(message, "⏳ Обновляю базу цен с сайта...")
            result = run_parser()
            if isinstance(result, list):
                bot.send_message(message.chat.id, f"✅ База успешно обновлена! Найдено позиций: {len(result)}")
            else:
                bot.send_message(message.chat.id, result)
        return

    # --- ВЫЗОВ GEMINI (/**) ---
    if msg_text.startswith('/**'):
        query = msg_text[3:].strip()
        if query:
            bot.send_chat_action(message.chat.id, 'typing')
            answer = get_ai_answer(query)
            bot.reply_to(message, answer)
        return

    # --- УМНЫЙ ПОИСК ПО KNOWLEDGE.TXT ---
    # Перебираем все блоки из файла
    for full_key in KNOWLEDGE.keys():
        # Разбиваем заголовок (например "ДОМА, ЦЕНЫ") на отдельные слова
        keywords = [k.strip().lower() for k in full_key.split(',')]
        
        # Если хоть одно слово-ключ есть в сообщении пользователя
        if any(word in msg_lower for word in keywords if len(word) > 2):
            bot.send_chat_action(message.chat.id, 'typing')
            
            # Если это Маршрут — выдаем текст с кнопками
            if any(r in keywords for r in ["маршрут", "доехать", "добраться"]):
                answer = sync_get_text(full_key)
                bot.send_message(message.chat.id, answer, reply_markup=get_route_keyboard(), parse_mode='Markdown')
            else:
                # Для всего остального (дома, правила, баня) — просто текст с ценами
                answer = sync_get_text(full_key)
                bot.send_message(message.chat.id, answer, parse_mode='Markdown', disable_web_page_preview=False)
            return

# 3. Обработчик нажатий на Inline-кнопки Маршрута
@bot.callback_query_handler(func=lambda call: call.data.startswith("ROUTE_"))
def callback_route(call):
    # Определяем, какой блок из файла подтянуть
    topic = "МАРШРУТ_АВТО" if call.data == "ROUTE_AUTO" else "МАРШРУТ_ОБЩЕСТВЕННЫЙ"
    answer = sync_get_text(topic)
    
    bot.send_message(call.message.chat.id, answer, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

# 4. Точка входа
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        print("✅ Бот 'Ботаничка' запущен!")
        bot.infinity_polling(timeout=30)
    except Exception as e:
        print(f"🔥 Ошибка: {e}")
