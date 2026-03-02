import os
import telebot
# Импортируем твои функции из соседних файлов
from gemini_handler import get_ai_answer
from db_worker import run_parser

# 1. Загрузка настроек из Render (Environment)
raw_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
BOT_TOKEN = raw_token.replace('"', '').replace("'", "")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# 2. Проверка токена перед запуском
if not BOT_TOKEN:
    print("❌ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN не найдена!")
elif ":" not in BOT_TOKEN:
    print(f"❌ ОШИБКА: Токен некорректен (нет двоеточия). Проверь Render.")

# 3. Инициализация бота (ЕДИНСТВЕННАЯ на весь проект)
bot = telebot.TeleBot(BOT_TOKEN)

# 4. Обработчик всех входящих сообщений
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    if not message.text:
        return

        # Команда обновления базы (только для админа)
    if message.text == '/update':
        if message.from_user.id == ADMIN_ID:
            bot.reply_to(message, "⏳ Начинаю парсинг сайта...")
            
            # Получаем результат (теперь это список)
            result = run_parser()
            
            if isinstance(result, list):
                # Формируем отчет из 15 строк
                report = f"<b>✅ База успешно обновлена!</b>\n"
                report += f"Найдено позиций: <b>{len(result)}</b>\n\n"
                
                for item in result:
                    url, title, price, content = item
                    # Если есть описание (для лодок/бани), добавляем его в скобках
                    line = f"• {title}: <b>{price} руб.</b>"
                    if content:
                        line += f" — <i>{content}</i>"
                    report += line + "\n"
                
                bot.send_message(message.chat.id, report, parse_mode='HTML', disable_web_page_preview=True)
            else:
                # Если вернулась строка с ошибкой
                bot.send_message(message.chat.id, result)
        else:
            bot.reply_to(message, "🔐 Доступ к обновлению только для администратора.")
        return


    # Вызов Gemini через префикс /**
    if message.text.startswith('/**'):
        query = message.text[3:].strip()
        if query:
            # Эффект "печатает..."
            bot.send_chat_action(message.chat.id, 'typing')
            # Вызов функции из gemini_handler.py
            answer = get_ai_answer(query)
            bot.reply_to(message, answer)
        else:
            bot.reply_to(message, "Напиши вопрос после /**, например: /** как дела?")

# 5. Точка входа
if __name__ == "__main__":
    try:
        print("🚀 Очистка старых соединений (Fix Error 409)...")
        # Принудительно сбрасываем старое подключение перед запуском
        bot.remove_webhook() 
        print("✅ Бот успешно запущен и слушает команды!")
        # Запускаем с чуть большими таймаутами для стабильности на Render
        bot.infinity_polling(timeout=30, long_polling_timeout=15)
    except Exception as e:
        print(f"🔥 Критическая ошибка при работе: {e}")

