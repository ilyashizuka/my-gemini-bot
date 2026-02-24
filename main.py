import requests
import re
from bs4 import BeautifulSoup
from db_worker import save_to_db

URL = "https://vuoksa-virta.ru/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

def clean_p(text):
    match = re.search(r'(\d[\d\s\xa0]*)', text)
    return re.sub(r'[^\d]', '', match.group(1)) if match else "0"

def parse_site():
    print("--- ЗАПУСК ПАРСИНГА V8 (СТРОГАЯ СТРУКТУРА) ---")
    try:
        res = requests.get(URL, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        main_phone = phone_tag['href'].replace('tel:', '') if phone_tag else "+79219930209"

        # 1. ПАРСИНГ ЛОДОК (Таблица #priceShip)
        ship_section = soup.find('figure', id='priceShip')
        if ship_section:
            table = ship_section.find('table')
            rows = table.find_all('tr')[1:] # Пропускаем заголовок
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    boat_name = cols[0].get_text(strip=True).replace(':', '')
                    price_res = clean_p(cols[1].text)
                    price_ext = clean_p(cols[2].text)
                    
                    save_to_db(f"{URL}#boat_{boat_name}_res", f"Лодки: {boat_name} (Для проживающих)", price_res, main_phone, "Тариф для гостей базы")
                    save_to_db(f"{URL}#boat_{boat_name}_ext", f"Лодки: {boat_name} (Без проживания)", price_ext, main_phone, "Тариф для внешних гостей")
                    print(f"✅ Лодка: {boat_name} сохранена")

        # 2. ПАРСИНГ САУНЫ (Таблица #priceSauna)
        sauna_section = soup.find('figure', id='priceSauna')
        if sauna_section:
            table = sauna_section.find('table')
            cols = table.find_all('td')
            if len(cols) >= 2:
                price_res = clean_p(cols[0].text)
                price_ext = clean_p(cols[1].text)
                desc = "Минимальный заказ от 3-х часов. Время растопки - 3 часа."
                
                save_to_db(f"{URL}#sauna_res", "Сауна (Для проживающих)", price_res, main_phone, desc)
                save_to_db(f"{URL}#sauna_ext", "Сауна (Без проживания)", price_ext, main_phone, desc)
                print(f"✅ Сауна сохранена")

        # 3. ПАРСИНГ ДОМОВ (H3)
        for h3 in soup.find_all('h3'):
            title = h3.get_text(strip=True).strip(':')
            # Игнорируем технические H3
            if any(x in title.lower() for x in ['меню', 'навигация', 'лодки', 'сауна', 'баня']): continue
            
            # Собираем данные только до следующего H3 или таблицы
            for sibling in h3.find_next_siblings():
                if sibling.name in ['h3', 'figure']: break
                text = sibling.get_text(strip=True)
                
                price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
                if price_match:
                    val = clean_p(price_match.group(1))
                    if int(val) > 200: # Фильтр мелких цен (типа белья за 300)
                        f_title = f"{title} (Доп. место)" if "дополнительно" in text.lower() else title
                        save_to_db(f"{URL}#{hash(f_title+val)}", f_title, val, main_phone, text[:500])
                        print(f"✅ Дом: {f_title} -> {val}")

        print("--- ПАРСИНГ ЗАВЕРШЕН ---")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    parse_site()
