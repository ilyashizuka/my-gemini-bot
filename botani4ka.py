import os
import re
import aiomysql

# Данные для подключения к Hostland (из твоего конфига)
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
    """Читает knowledge.txt и разбивает на блоки по === заголовок ==="""
    file_path = "knowledge.txt"
    if not os.path.exists(file_path):
        print(f"❌ ОШИБКА: Файл {file_path} не найден!")
        return {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Режем по разделителю ===
    blocks = re.split(r'===', content)
    kb = {}
    for i in range(1, len(blocks), 2):
        # Очищаем ключи (заголовки через запятую) и в верхний регистр
        keys = [k.strip().upper() for k in blocks[i].split(',')]
        body = blocks[i+1].strip()
        for key in keys:
            kb[key] = body
    return kb

async def get_formatted_text(topic_key):
    """Сборка текста: Шаблон из файла + Цены из таблицы parsed_content"""
    kb = load_knowledge()
    template = kb.get(topic_key.upper(), f"Информация по запросу '{topic_key}' не найдена.")
    
    # КАРТА СООТВЕТСТВИЯ (URL из твоего парсера -> Теги в твоем файле)
    mapping = {
        "https://vuoksa-virta.ru#5-ka": "price_house_5",
        "https://vuoksa-virta.ru#homewithsauna": "price_srub",
        "https://vuoksa-virta.ru#figwam": "price_bungalo",
        "https://vuoksa-virta.ru#nomernadellingom": "price_komunalka",
        "https://vuoksa-virta.ru#studia": "price_studio",
        "https://vuoksa-virta.ru#sauna_in": "price_sauna_in",
        "https://vuoksa-virta.ru#sauna_out": "price_sauna_out"
    }

    conn = None
    try:
        # Подключаемся асинхронно к MySQL
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cur:
            # Выбираем данные, которые вчера/сегодня записал парсер
            await cur.execute("SELECT url, price FROM parsed_content")
            rows = await cur.fetchall()
            
            # Собираем словарь цен для метода .format()
            prices = {}
            for row in rows:
                url = row['url']
                if url in mapping:
                    # Очищаем цену от 'рублей' и пробелов, оставляем только цифры
                    val = str(row['price'])
                    clean_price = re.sub(r'\D', '', val)
                    prices[mapping[url]] = clean_price
            
            # Добавляем константы, которых нет в парсере
            prices['price_linen'] = "300"
            prices['price_extra_bed'] = "1000"

            # Магия подстановки цен в фигурные скобки {price_...}
            return template.format(**prices)
            
    except Exception as e:
        print(f"⚠️ Ошибка сборки текста в ботаничке: {e}")
        # Если база не ответила, отдаем текст как есть
        return template
    finally:
        if conn:
            conn.close()
