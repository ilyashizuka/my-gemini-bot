import requests
import re
from bs4 import BeautifulSoup
from db_worker import save_to_db

URL = "https://vuoksa-virta.ru"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}

def start_single_page_parsing():
    print(f"--- ПАРСИНГ ОДНОСТРАНИЧНИКА: {URL} ---")
    try:
        res = requests.get(URL, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"Ошибка доступа: {res.status_code}")
            return

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Ищем телефон (берем первый найденный)
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "Нет"

        # 2. Ищем ВСЕ блоки, где упоминается цена (число + руб)
        # Ищем текст во всех тегах (p, li, td, span, div)
        count = 0
        items = soup.find_all(['p', 'li', 'td', 'span', 'div'])
        
        found_data = set() # Чтобы не дублировать одинаковые строки

        for item in items:
            text = item.get_text(strip=True)
            # Регулярка: ищем текст, где есть число и "руб"
            if re.search(r'\d.*руб', text) and len(text) < 200:
                if text not in found_data:
                    # Извлекаем только цифры цены из этой строки
                    price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
                    price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else "0"
                    
                    # Название услуги — это весь текст строки
                    title = text.split(price)[0].strip().strip(':').strip('-')
                    if not title: title = "Услуга/Товар"

                    # Сохраняем в базу (используем текст как часть URL для уникальности)
                    unique_id = f"{URL}#{hash(text)}"
                    save_to_db(unique_id, title, price, phone, text)
                    
                    print(f"✅ Найдено: {title} -> {price} руб.")
                    found_data.add(text)
                    count += 1

        print(f"--- ЗАВЕРШЕНО. Найдено позиций: {count} ---")

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    start_single_page_parsing()
