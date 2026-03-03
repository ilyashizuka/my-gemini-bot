import os
import re
import aiomysql

# Настройки те же, что в парсере
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
    if not os.path.exists("knowledge.txt"): return {}
    with open("knowledge.txt", "r", encoding="utf-8") as f:
        content = f.read()
    blocks = re.split(r'===', content)
    kb = {}
    for i in range(1, len(blocks), 2):
        keys = [k.strip().upper() for k in blocks[i].split(',')]
        body = blocks[i+1].strip()
        for key in keys: kb[key] = body
    return kb

async def get_formatted_text(topic_key):
    kb = load_knowledge()
    template = kb.get(topic_key.upper(), f"Информация {topic_key} не найдена.")
    
    # Карта соответствия: URL из парсера -> Ключ в knowledge.txt
    mapping = {
        "https://vuoksa-virta.ru#5-ka": "price_house_5",
        "https://vuoksa-virta.ru#homewithsauna": "price_srub",
        "https://vuoksa-virta.ru#figwam": "price_bungalo",
        "https://vuoksa-virta.ru#nomernadellingom": "price_komunalka",
        "https://vuoksa-virta.ru#studia": "price_studio"
    }

    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cur:
            # Читаем из таблицы, которую заполнил парсер
            await cur.execute("SELECT url, price FROM parsed_content")
            rows = await cur.fetchall()
            
            # Собираем словарь цен, переводя URL в понятные боту ключи
            prices = {}
            for row in rows:
                if row['url'] in mapping:
                    prices[mapping[row['url']]] = str(row['price'])
            
            # Добавляем константы
            prices['price_linen'] = "300"
            prices['price_extra_bed'] = "1000"

            return template.format(**prices)
    except Exception as e:
        print(f"❌ Ошибка стыковки с БД: {e}")
        return template
    finally:
        if 'conn' in locals(): conn.close()
