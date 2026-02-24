import telebot
import pymysql
import os
from db_worker import DB_CONFIG
from main import parse_site  # Импортируем ваш парсер

TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 6503375  # ЗАМЕНИТЕ на ваш Telegram ID (можно узнать у @userinfobot)

bot = telebot.TeleBot(TOKEN)

# Функция поиска в БД (остается прежней)
def get_data_from_db(search_query):
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            sql = "SELECT title, price, phone, content FROM parsed_content WHERE title LIKE %s OR content LIKE %s LIMIT 5"
            cursor.execute(sql, (f'%{search_query}%', f'%{search_query}%'))
            return cursor.fetchall()
    finally:
        connection.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🏠 Бот базы «Вуокса-Вирта» готов к работе!\n\nНапишите название (например: лодка, сауна, дом), чтобы узнать цену.")

# КОМАНДА ДЛЯ ОБНОВЛЕНИЯ БАЗЫ
@bot.message_handler(commands=['update'])
def run_update(message):
    # Проверка, что команду прислал именно админ
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "⏳ Начинаю парсинг сайта... Это займет около 30 секунд.")
        try:
            parse_site() # Запуск функции из main.py
            bot.edit_message_text("✅ База данных успешно обновлена!", message.chat.id, msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка при парсинге: {e}", message.chat.id, msg.message_id)
    else:
        bot.reply_to(message, "⛔ У вас нет прав для выполнения этой команды.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    query = message.text.strip().lower()
    if len(query) < 2: return

    results = get_data_from_db(query)
    if not results:
        bot.send_message(message.chat.id, "Ничего не найдено. Попробуйте: лодка, сауна или название дома.")
    else:
        for row in results:
            price = f"{row['price']} руб." if row['price'] != "0" else "По запросу"
            text = f"🏨 *{row['title']}*\n💰 Цена: {price}\n📞 Тел: {row['phone']}"
            bot.send_message(message.chat.id, text, parse_mode="Markdown")

if __name__ == "__main__":
    print("Бот запущен и ждет команд...")
    bot.infinity_polling()
