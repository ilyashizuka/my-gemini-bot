import os
import re
import aiomysql

# Конфигурация БД (Hostland)
DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': os.environ.get('DB_PASSWORD'),
    'db': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': aiomysql.DictCursor,
}

def load_knowledge():
    """Чтение файла и разбивка на блоки"""
    file_path = "knowledge.txt"
    if not os.path.exists(file_path): return {}
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = re.split(r'===', content)
    kb = {}
    for i in range(1, len(blocks), 2):
        keys = [k.strip().upper() for k in blocks[i].split(',')]
        body = blocks[i+1].strip()
        for key in keys: kb[key] = body
    return kb

async def get_formatted_text(topic_key):
    """Сборка текста: Шаблон из файла + Цены из ТВОЕЙ таблицы parsed_content"""
    kb = load_knowledge()
    template = kb.get(topic_key.upper(), "Инфо не найдено.")
    
    # Карта: какой URL на сайте соответствует какому тегу в твоем файле
    mapping = {
        "https://vuoksa-virta.ru#5-ka": "price_house_5",
        "https://vuoksa-virta.ru#homewithsauna": "price_srub",
        "https://vuoksa-virta.ru#figwam": "price_bungalo",
        "https://vuoksa-virta.ru#nomernadellingom": "price_komunalka",
        "https://vuoksa-virta.ru#studia": "price_studio"
    }

    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cur:
            # Твоя таблица: parsed_content, поля: url и price
            await cur.execute("SELECT url, price FROM parsed_content")
            rows = await cur.fetchall()
            
            # Превращаем данные из базы в ключи для .format()
            prices = {}
            for row in rows:
                url = row['url']
                if url in mapping:
                    # Чистим цену от лишних знаков (на всякий случай)
                    clean_price = re.sub(r'\D', '', str(row['price']))
                    prices[mapping[url]] = clean_price
            
            # Добавляем константы, которых нет в парсере
            prices['price_linen'] = "300"
            prices['price_extra_bed'] = "1000"

            # Магия: вставляем цифры в {price_house_5} и т.д.
            return template.format(**prices)
            
    except Exception as e:
        print(f"⚠️ Ошибка MySQL: {e}")
        return template
    finally:
        if conn: conn.close()
