import requests
import re
from bs4 import BeautifulSoup
from db_worker import save_to_db

URL = "https://vuoksa-virta.ru"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}

def parse_site():
    print(f"--- НАЧАЛО СТРУКТУРИРОВАННОГО СБОРА ---")
    try:
        res = requests.get(URL, headers=HEADERS, timeout=20)
        if res.status_code != 200: return
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. ТЕЛЕФОН (для трансфера и справок)
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        main_phone = phone_tag['href'].replace('tel:', '') if phone_tag else "+79219930209"

        # 2. ОПРЕДЕЛЯЕМ КАТЕГОРИИ (ищем блоки по ключевым словам в заголовках)
        sections = soup.find_all(['section', 'div', 'article'])
        
        results = []

        for sec in sections:
            sec_text = sec.get_text(separator=' ', strip=True).lower()
            
            # А) ЛОДКИ (учитываем условие для проживающих/непроживающих)
            if 'прокат' in sec_text and 'лод' in sec_text:
                rows = sec.find_all(['tr', 'p', 'li'])
                for r in rows:
                    t = r.get_text(strip=True)
                    if 'руб' in t:
                        results.append(("Прокат лодок", t, main_phone))

            # Б) ПРОЖИВАНИЕ (Дома, Студия, Терраса)
            elif any(word in sec_text for word in ['террас', 'студия', 'дом']):
                title_tag = sec.find(['h2', 'h3', 'h4'])
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    price_match = re.search(r'(\d[\d\s\xa0]*)руб', sec_text)
                    if price_match:
                        results.append((title, price_match.group(1), main_phone))

            # В) САУНА
            elif 'сауна' in sec_text or 'баня' in sec_text:
                price_match = re.search(r'(\d[\d\s\xa0]*)руб', sec_text)
                if price_match:
                    results.append(("Сауна", price_match.group(1), main_phone))

            # Г) ТРАНСФЕР
            elif 'трансфер' in sec_text:
                results.append(("Трансфер", "По запросу (см. телефон)", main_phone))

        # 3. СОХРАНЕНИЕ УНИКАЛЬНЫХ ДАННЫХ
        final_count = 0
        seen = set()
        for res_title, res_price, res_phone in results:
            # Чистим цену
            clean_p = re.sub(r'[^\d]', '', str(res_price)) if any(char.isdigit() for char in str(res_price)) else "0"
            
            # Чтобы не дублировать
            entry_id = f"{res_title}_{clean_p}"
            if entry_id not in seen and len(res_title) < 100:
                save_to_db(f"{URL}#{hash(entry_id)}", res_title, clean_p, res_phone, res_price)
                print(f"✅ Сохранено: {res_title} | {clean_p} руб.")
                seen.add(entry_id)
                final_count += 1

        print(f"--- ГОТОВО. Сохранено записей: {final_count} ---")

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    parse_site()
