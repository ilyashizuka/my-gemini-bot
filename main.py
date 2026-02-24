import requests
import re
from bs4 import BeautifulSoup
from db_worker import save_to_db

URL = "https://vuoksa-virta.ru"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}

def start_precise_parsing():
    print(f"--- ТОЧЕЧНЫЙ ПАРСИНГ ПО СТРУКТУРЕ H3: {URL} ---")
    try:
        res = requests.get(URL, headers=HEADERS, timeout=20)
        if res.status_code != 200: return
        soup = BeautifulSoup(res.text, 'html.parser')

        # Общий телефон
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "+79219930209"

        # Находим все заголовки H3 (это названия ваших домов/услуг)
        sections = soup.find_all('h3')
        
        count = 0
        for h3 in sections:
            title = h3.get_text(strip=True).strip(':')
            
            # Игнорируем мусорные заголовки меню
            if any(x in title.lower() for x in ['меню', 'навигация', 'главная', 'контакты']):
                continue

            # Ищем данные в блоке ПОСЛЕ заголовка H3 (описание и цена)
            content_parts = []
            price = "0"
            
            # Перебираем все элементы после текущего H3 до следующего H3
            for sibling in h3.find_next_siblings():
                if sibling.name == 'h3': break # Дошли до следующего домика - стоп
                
                text = sibling.get_text(strip=True)
                if not text: continue
                
                # Добавляем в описание
                content_parts.append(text)
                
                # Ищем цену в текущем элементе
                # Ищем число перед "рублей" или "руб"
                price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
                if price_match:
                    # Если в блоке несколько цен (основная и за раскладушку), 
                    # мы можем либо брать первую, либо создавать доп. записи.
                    current_price = re.sub(r'[^\d]', '', price_match.group(1))
                    
                    # Если это "Дополнительно" или "Раскладушка" - уточняем заголовок
                    final_title = title
                    if "дополнительно" in text.lower() or "раскладушка" in text.lower():
                        final_title = f"{title} (Доп. место)"
                    
                    description = " ".join(content_parts)[:1000] # Собираем описание
                    
                    # Сохранение в БД
                    unique_id = f"{URL}#{hash(final_title + current_price)}"
                    save_to_db(unique_id, final_title, current_price, phone, description)
                    
                    print(f"✅ Сохранено: {final_title} -> {current_price} руб.")
                    count += 1

        print(f"--- ЗАВЕРШЕНО. Сохранено позиций: {count} ---")

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    start_precise_parsing()
