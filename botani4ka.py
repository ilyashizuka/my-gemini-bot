import os
import re
import aiomysql

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
    template = kb.get(topic_key.upper(), "Инфо не найдено.")
    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cur:
            await cur.execute("SELECT name, value FROM prices")
            rows = await cur.fetchall()
            prices = {row['name']: str(row['value']) for row in rows}
            prices['price_linen'] = "300"
            return template.format(**prices)
    except Exception: return template
    finally:
        if conn: conn.close()
