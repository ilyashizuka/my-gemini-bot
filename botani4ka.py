import os
import re
import asyncio
import aiomysql
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- БЛОК 1: ПОДКЛЮЧЕНИЕ К ВАШЕЙ БД НА HOSTLAND ---
DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': os.environ.get('DB_PASSWORD'),
    'db': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': aiomysql.DictCursor,
}

# --- БЛОК 2: ПАРСЕР ТЕКСТОВОГО ФАЙЛА KNOWLEDGE.TXT ---
def load_knowledge():
    if not os.path.exists("knowledge.txt"):
        return {}
    with open("knowledge.txt", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Режем файл по разделителю ===
    blocks = re.split(r'===', content)
    kb = {}
    for i in range(1, len(blocks), 2):
        # Ключи из заголовка (через запятую) превращаем в список
        keys = [k.strip().upper() for k in blocks[i].split(',')]
        body = blocks[i+1].strip()
        for key in keys:
            kb[key] = body
    return kb

# Загружаем базу знаний в память при старте
KNOWLEDGE_BASE = load_knowledge()

# --- БЛОК 3: ФУНКЦИЯ СБОРКИ ТЕКСТА (Файл + БД) ---
async def get_formatted_text(topic_key):
    # Достаем шаблон из файла
    template = KNOWLEDGE_BASE.get(topic_key.upper(), "Инфо не найдено 🤷‍♂️")
    
    # Идем в MySQL за ценами
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cur:
            await cur.execute("SELECT name, value FROM prices") # name - это price_house_5 и т.д.
            rows = await cur.fetchall()
            # Делаем словарь {'price_house_5': '7000', ...}
            prices = {row['name']: str(row['value']) for row in rows}
            # Добавляем константу белья вручную
            prices['price_linen'] = "300"
            # Подставляем цены в текст
            return template.format(**prices)
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return template # Если БД лежит, отдаем текст с тегами
    finally:
        if 'conn' in locals() and conn: conn.close()

# --- БЛОК 4: САМ БОТ ---
bot = Bot(token=os.environ.get('BOT_TOKEN')) # Токен тоже лучше в Рендере прописать
dp = Dispatcher()

# Обработка команды /start в группе
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Берем вводный блок из файла
    text = await get_formatted_text("ВАРИАНТЫ_ПРОЖИВАНИЯ")
    await message.answer(text, parse_mode="Markdown")

# Обработка кнопок (если прикрутим Inline) или просто текста
@dp.callback_query(F.data.startswith("INFO_"))
async def handle_buttons(callback: types.CallbackQuery):
    topic = callback.data.replace("INFO_", "") # Например: ПЯТЕРОЧКА
    text = await get_formatted_text(f"ОПИСАНИЕ_{topic}")
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
