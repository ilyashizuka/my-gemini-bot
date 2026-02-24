import requests
import re
from bs4 import BeautifulSoup
from db_worker import save_to_db

URL = "https://vuoksa-virta.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

def clean_p(text):
    match = re.search(r'(\d[\d\s\xa0]*)', text)
    return re.sub(r'[^\d]', '', match.group(1)) if match else "0"

def parse_site():
    print("--- ЗАПУСК ПОЛНОГО СТРУКТУРИРОВАННОГО ПАРСИНГА ---")
    try:
        res = requests.get(URL, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. ТРАНСФЕР (По id="transfer")
        transfer_block = soup.find(id='transfer')
        if transfer_block:
            t_text = transfer_block.get_text(strip=True)
            # Ищем телефон именно в этом блоке
            t_phone_tag = transfer_block.find('a', href=re.compile(r'^tel:'))
            t_phone = t_phone_tag['href'].replace('tel:', '').replace('"', '') if t_phone_tag else "+79219327491"
            
            save_to_db(f"{URL}#transfer", "Трансфер (Лосево - База)", "0", t_phone, t_text[:500])
            print(f"✅ Трансфер сохранен: {t_phone}")

        # Основной телефон для всего остального
        main_phone = "+79219930209"

        # 2. ЛОДКИ (Таблица #priceShip)
        ship_section = soup.find('figure', id='priceShip')
        if ship_section:
            rows = ship_section.find('table').find_all('tr')[1:]
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    name = cols[0].get_text(strip=True).replace(':', '')
                    save_to_db(f"{URL}#boat_{name}_res", f"Лодки: {name} (Для проживающих)", clean_p(cols[1].text), main_phone, "Тариф для гостей базы")
                    save_to_db(f"{URL}#boat_{name}_ext", f"Лодки: {name} (Без проживания)", clean_p(cols[2].text), main_phone, "Тариф для внешних гостей")
            print("✅ Таблица лодок обработана")

        # 3. САУНА (Таблица #priceSauna)
        sauna_section = soup.find('figure', id='priceSauna')
        if sauna_section:
            cols = sauna_section.find('table').find_all('td')
            if len(cols) >= 2:
                save_to_db(f"{URL}#sauna_res", "Сауна (Для проживающих)", clean_p(cols[0].text), main_phone, "Мин. 3 часа")
                save_to_db(f"{URL}#sauna_ext", "Сауна (Без проживания)", clean_p(cols[1].text), main_phone, "Мин. 3 часа")
            print("✅ Таблица сауны обработана")

        # 4. ДОМА (H3)
        for h3 in soup.find_all('h3'):
            title = h3.get_text(strip=True).strip(':')
            if any(x in title.lower() for x in ['меню', 'навигация', 'лодки', 'сауна']): continue
            
            for sibling in h3.find_next_siblings():
                if sibling.name in ['h3', 'figure']: break
                text = sibling.get_text(strip=True)
                price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
                if price_match:
                    val = clean_p(price_match.group(1))
                    if int(val) > 400: # Отсекаем мелкие услуги
                        f_title = f"{title} (Доп. место)" if "дополнительно" in text.lower() else title
                        save_to_db(f"{URL}#{hash(f_title+val)}", f_title, val, main_phone, text[:500])
                        print(f"✅ Дом/Услуга: {f_title} -> {val}")

        print("--- ПАРСИНГ УСПЕШНО ЗАВЕРШЕН ---")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    parse_site()
