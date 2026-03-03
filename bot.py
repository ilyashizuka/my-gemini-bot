import os
import re
import aiomysql

# Данные для подключения (из твоего конфига)
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
    """Читает knowledge.txt и режет его на блоки по === заголовок ==="""
    if not os.path.exists("knowledge.txt"):
        print("❌ Файл knowledge.txt не найден!")
        return {}
    with open("knowledge.txt", "r", encoding="utf-8") as f:
        content = f.read()
    
    blocks = re.split(r'===', content)
    kb = {}
    for i in range(1, len(blocks), 2):
        # Очищаем заголовки (ключи) и переводим в верхний регистр
        keys = [k.strip().upper() for k in blocks[i].split(',')]
        body = blocks[i+1].strip()
        for key in keys:
            kb[key] = body
    return kb

async def get_formatted_text(topic_key):
    """Берет текст из файла и вставляет цены из MySQL"""
    # Подгружаем базу (в bot.py она уже загружена, но тут для страховки)
    kb = load_knowledge()
    template = kb.get(topic_key.upper(), f"Информация по запросу '{topic_key}' не найдена.")
    
    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cur:
            # name — ключ (price_house_5), value — цена
            await cur.execute("SELECT name, value FROM prices")
            rows = await cur.fetchall()
            
            # Собираем словарь цен
            prices = {row['name']: str(row['value']) for row in rows}
            # Константы, которых нет в БД
            prices['price_linen'] = "300"
            
            # Форматируем шаблон данными из БД
            return template.format(**prices)
    except Exception as e:
        print(f"⚠️ Ошибка MySQL: {e}")
        # Если база упала, возвращаем текст как есть (с тегами {price})
        return template
    finally:
        if conn:
            conn.close()
