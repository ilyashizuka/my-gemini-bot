import telebot
import pymysql
import os
from db_worker import DB_CONFIG # Используем настройки из вашего файла

# Токен вашего бота (замените на свой или добавьте в Environment Variables на Render)
TOKEN = os.getenv('BOT_TOKEN', 'ВАШ_ТЕЛЕГРАМ_ТОКЕН')
bot = telebot.TeleBot(TOKEN)

def get_data_from_db(search_query):
    """Ищет услуги и цены в базе данных host1324224_botanik"""
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # Ищем частичное совпадение в названии или описании
            sql = "SELECT title, price, phone, content FROM parsed_content WHERE title LIKE %s OR content LIKE %s LIMIT 5"
            cursor.execute(sql, (f'%{search_query}%', f'%{search_query}%'))
            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return []
    finally:
        connection.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот базы «Вуокса-Вирта». Напишите название услуги (например: лодка, сауна, дом), и я пришлю актуальную цену.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    query = message.text.strip().lower()
    
    if len(query) < 3:
        bot.send_message(message.chat.id, "Введите хотя бы 3 буквы для поиска.")
        return

    results = get_data_from_db(query)
    
    if not results:
        bot.send_message(message.chat.id, f"К сожалению, по запросу «{query}» ничего не найдено. Попробуйте другое слово.")
    else:
        response = "🔍 Вот что я нашел:\n\n"
        for row in results:
            price_str = f"{row['price']} руб." if row['price'] != "0" else "По запросу"
            response += f"🏠 *{row['title']}*\n💰 Цена: {price_str}\n📞 Тел: {row['phone']}\n\n"
        
        bot.send_message(message.chat.id, response, parse_mode="Markdown")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
