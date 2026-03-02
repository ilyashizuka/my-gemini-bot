import os
import re
import requests
import pymysql
from bs4 import BeautifulSoup
from telebot import TeleBot

# --- НАСТРОЙКИ ИЗ СЕКРЕТОВ (RENDER) ---
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c') 
ADMIN_ID = int(os.getenv('ADMIN_ID', 0)) 
BOT_TOKEN = os.getenv('BOT_TOKEN') # Токен твоего бота

bot = TeleBot(BOT_TOKEN)

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def extract_price(element):
    """Ищет числовое значение перед словом 'рублей' в элементе"""
    if not element:
        return "0"
    text = element.get_text(separator=' ', strip=True).replace('\xa0', ' ')
    match = re.search(r'(\d[\d\s]*)\s*рублей', text)
    if match:
        # Убираем пробелы внутри числа (например "1 500" -> "1500")
        return re.sub(r'\D', '', match.group(1))
    return "0"

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = [] # Список для пакетной вставки в БД
    
    try:
        # 1. Загружаем главную и ищем меню
        response = requests.get(base_url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        menu = soup.find(id='menu')
        
        if not menu:
            return "Ошибка: Блок id='menu' не найден на главной странице."
        
        # Собираем ссылки из меню (убираем дубликаты через set)
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href']
            full_url = href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}"
            links.add(full_url)

        # 2. Обходим каждую страницу из меню
        for url in links:
            page_res = requests.get(url, timeout=15)
            page_soup = BeautifulSoup(page_res.content, 'html.parser')

            # --- А) Парсинг объектов по H3 с ID (Домики и т.д.) ---
            for h3 in page_soup.find_all('h3', id=True):
                # Игнорируем заголовки внутри спец. таблиц (баня/лодки), их парсим отдельно ниже
                if h3.find_parent('figure', id=['priceShip', 'priceSauna']):
                    continue
                
                title = h3.get_text(strip=True)
                # Ищем цену в ближайшем контексте заголовка
                price = extract_price(h3.find_next())
                all_data.append((url, title, price, title))

            # --- Б) Парсинг таблицы ЛОДКИ (id=priceShip) ---
            ship_fig = page_soup.find('figure', id='priceShip')
            if ship_fig:
                # Берем все строки tr кроме заголовка
                rows = ship_fig.find_all('tr')[1:]
                for row in rows:
                    tds = row.find_all('td')
                    if len(tds) >= 3:
                        tariff = tds[0].get_text(strip=True)
                        # Чистим цену для 2-й и 3-й колонки
                        price_in = extract_price(tds[1])
                        price_out = extract_price(tds[2])
                        
                        # Запись для проживающих
                        all_data.append((url, "Прокат лодки Пелла", price_in, f"прокат лодки Пелла тариф {tariff} для проживающих"))
                        # Запись для непроживающих
                        all_data.append((url, "Прокат лодки Пелла", price_out, f"прокат лодки Пелла тариф {tariff} для непроживающих"))

            # --- В) Парсинг таблицы БАНЯ (id=priceSauna) ---
            sauna_fig = page_soup.find('figure', id='priceSauna')
            if sauna_fig:
                rows = sauna_fig.find_all('tr')[1:]
                for row in rows:
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        price_in = extract_price(tds[0])
                        price_out = extract_price(tds[1])
                        
                        all_data.append((url, "Баня на дровах", price_in, "баня на дровах для проживающих"))
                        all_data.append((url, "Баня на дровах", price_out, "баня на дровах для непроживающих"))

        # 3. Работа с базой данных
        if not all_data:
            return "Парсинг завершен: данных не найдено."

        connection = pymysql.connect(**DB_CONFIG)
        try:
            with connection.cursor() as cursor:
                # Полная очистка перед обновлением
                cursor.execute("DELETE FROM `parsed_content`")
                
                # Массовая вставка всех собранных данных
                sql = "INSERT INTO `parsed_content` (`url`, `title`, `price`, `content`) VALUES (%s, %s, %s, %s)"
                cursor.executemany(sql, all_data)
                
                connection.commit()
            return f"✅ База успешно обновлена! Добавлено записей: {len(all_data)}"
        finally:
            connection.close()

    except Exception as e:
        return f"❌ Ошибка при парсинге: {str(e)}"

# --- ОБРАБОТЧИК КОМАНДЫ /UPDATE ---
@bot.message_handler(commands=['update'])
def handle_update(message):
    # Проверка: ID пользователя из телеграм == ADMIN_ID из секретов Render
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🔄 Запускаю парсер... Это займет несколько секунд.")
        result_text = run_parser()
        bot.send_message(message.chat.id, result_text)
    else:
        bot.send_message(message.chat.id, "🔒 Извините, эта команда доступна только администратору.")

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен и готов к работе...")
    bot.infinity_polling()
