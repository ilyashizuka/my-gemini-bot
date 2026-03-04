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

# Защита от падения бота при отсутствии ключа в БД
class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'

def load_knowledge():
    """Читает файл и режет на блоки по === заголовок ==="""
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
    """Сборка текста: Шаблон из файла + Цены из БД по URL-хвостам"""
    kb = load_knowledge()
    target_key = topic_key.upper()
    template = kb.get(target_key)
    
    # Поиск по вхождению (если ключ сложный)
    if not template:
        for k, v in kb.items():
            if target_key in k:
                template = v
                break
    
    if not template: return f"Информация по запросу {topic_key} не найдена."

    # КАРТА: Хвост URL в базе -> Тег в знании (knowledge.txt)
    mapping = {
        "#5-ka": "price_house_5",
        "#homewithsauna": "price_srub",
        "#figwam": "price_bungalo",
        "#nomernadellingom": "price_komunalka",
        "#studia": "price_studio",
        "#sauna_in": "price_sauna_in",
        "#sauna_out": "price_sauna_out",
        "#boat_in_0": "price_mirage_day_in",
        "#boat_out_0": "price_mirage_day_out",
        "#boat_in_1": "price_mirage_sutki_in",
        "#boat_out_1": "price_mirage_sutki_out",
        "#boat_in_2": "price_pella_day_in",
        "#boat_out_2": "price_pella_day_out",
        "#boat_in_3": "price_pella_sutki_in",
        "#boat_out_3": "price_pella_sutki_out"
    }

    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cur:
            await cur.execute("SELECT url, price FROM parsed_content")
            rows = await cur.fetchall()
            
            # Используем безопасный словарь
            prices_data = SafeDict()
            for row in rows:
                db_url = row['url']
                for suffix, tag in mapping.items():
                    if suffix in db_url:
                        # Чистим цену: оставляем только цифры
                        clean_val = re.sub(r'\D', '', str(row['price']))
                        prices_data[tag] = clean_val
            
            # Константы
            prices_data.update({"price_linen": "300", "price_extra_bed": "1000"})
            
            # Подставляем данные в шаблон через безопасный метод
            return template.format_map(prices_data)
            
    except Exception as e:
        print(f"❌ Ошибка в ботаничке: {e}")
        return template
    finally:
        if conn: conn.close()
