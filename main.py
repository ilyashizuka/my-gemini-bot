import requests
import re
from bs4 import BeautifulSoup
from db_worker import save_to_db

URL = "https://vuoksa-virta.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

def clean_p(text):
    return re.sub(r'[^\d]', '', text) if any(c.isdigit() for c in text) else "0"

def parse_site():
    print(f"--- ЗАПУСК ПАРСИНГА (ЕДИНОРАЗОВЫЙ) ---")
    try:
        res = requests.get(URL, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Основной телефон
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        main_phone = phone_tag['href'].replace('tel:', '') if phone_tag else "+79219930209"

        # 2. ПАРСИНГ ТАБЛИЦ (Лодки)
        tables = soup.find_all('table')
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            # Ищем таблицу, где есть "проживающих"
            if any("проживающих" in h.lower() for h in headers):
                rows = table.find_all('tr')[1:] # Пропускаем шапку
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        service_name = cols[0].get_text(strip=True).strip(':')
                        # Записываем тариф "Для проживающих"
                        save_to_db(f"{URL}#boat_{service_name}_resident", 
                                   f"Прокат: {service_name} (Для проживающих)", 
                                   clean_p(cols[1].text), main_phone, "Тариф для гостей базы")
                        # Записываем тариф "Без проживания"
                        save_to_db(f"{URL}#boat_{service_name}_external", 
                                   f"Прокат: {service_name} (Без проживания)", 
                                   clean_p(cols[2].text), main_phone, "Тариф для внешних гостей")

        # 3. ПАРСИНГ ДОМОВ (H3)
        for h3 in soup.find_all('h3'):
            title = h3.get_text(strip=True).strip(':')
            if any(x in title.lower() for x in ['меню', 'навигация', 'лодки']): continue
            
            content_parts = []
            for sibling in h3.find_next_siblings():
                if sibling.name == 'h3' or sibling.name == 'figure': break
                text = sibling.get_text(strip=True)
                content_parts.append(text)
                
                # Ищем цену в тексте
                price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
                if price_match:
                    p_val = clean_p(price_match.group(1))
                    f_title = f"{title} (Доп. место)" if "дополнительно" in text.lower() else title
                    save_to_db(f"{URL}#{hash(f_title+p_val)}", f_title, p_val, main_phone, " ".join(content_parts)[:500])
                    print(f"✅ Сохранено: {f_title} -> {p_val}")

        print("--- РАБОТА ЗАВЕРШЕНА ---")

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    parse_site()
    # Скрипт просто завершается здесь, никакого бесконечного цикла.
