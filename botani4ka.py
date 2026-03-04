import os
import re
import aiomysql

# Конфигурация БД (Hostland) — по твоему конфигу из парсера
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
    """Чтение файла и разбивка на блоки по === заголовок ==="""
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
    """Сборка текста: Шаблон + Цены из таблицы parsed_content по URL"""
    kb = load_knowledge()
    
    # Поиск шаблона в файле
    target_key = topic_key.upper()
    template = kb.get(target_key)
    if not template:
        for k, v in kb.items():
            if target_key in k:
                template = v
                break
    
    if not template:
        return f"Информация по запросу {topic_key} не найдена."

    # КАРТА: URL из твоего парсера -> Тег в knowledge.txt
    mapping = {
        # Домики (Content у них NULL, поэтому ищем по URL)
        "https://vuoksa-virta.ru#5-ka": "price_house_5",
        "https://vuoksa-virta.ru#homewithsauna": "price_srub",
        "https://vuoksa-virta.ru#figwam": "price_bungalo",
        "https://vuoksa-virta.ru#nomernadellingom": "price_komunalka",
        "https://vuoksa-virta.ru#studia": "price_studio",
        
        # Баня на дровах
        "https://vuoksa-virta.ru#sauna_in": "price_sauna_in",
        "https://vuoksa-virta.ru#sauna_out": "price_sauna_out",
        
        # Лодки Мираж
        "https://vuoksa-virta.ru#boat_in_0": "price_mirage_day_in",
        "https://vuoksa-virta.ru#boat_out_0": "price_mirage_day_out",
        "https://vuoksa-virta.ru#boat_in_1": "price_mirage_sutki_in",
        "https://vuoksa-virta.ru#boat_out_1": "price_mirage_sutki_out",
        
        # Лодки Пелла
        "https://vuoksa-virta.ru#boat_in_2": "price_pella_day_in",
        "https://vuoksa-virta.ru#boat_out_2": "price_pella_day_out",
        "https://vuoksa-virta.ru#boat_in_3": "price_pella_sutki_in",
        "https://vuoksa-virta.ru#boat_out_3": "price_pella_sutki_out"
    }

    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cur:
            # Читаем все записи из таблицы parsed_content
            await cur.execute("SELECT url, price FROM parsed_content")
            rows = await cur.fetchall()
            
            # Собираем словарь цен
            prices_dict = {}
            for row in rows:
                db_url = row['url']
                db_price = str(row['price'])
                
                # Проверяем, есть ли URL из базы в нашей карте
                for site_url, tag in mapping.items():
                    if site_url == db_url:
                        # Очищаем цену (оставляем только цифры)
                        clean_price = re.sub(r'\D', '', db_price)
                        prices_dict[tag] = clean_price
            
            # Добавляем константы (белье и доп.место)
            prices_dict.update({
                "price_linen": "300",
                "price_extra_bed": "1000"
            })

            # Подставляем цены в фигурные скобки {price_...}
            return template.format(**prices_dict)
            
    except Exception as e:
        print(f"⚠️ Ошибка в ботаничке: {e}")
        return template
    finally:
        if conn:
            conn.close()
