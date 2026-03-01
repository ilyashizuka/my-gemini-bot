import os
import pymysql

# Пытаемся взять пароль из секретов GitHub, если не находим — берем локальный
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c') 

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': DB_PASSWORD, # Используем переменную
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def save_to_db(url, title, price, phone, content=""):
    connection = None
    try:
        print(f"--- БД: Очистка и сохранение {url} ---", flush=True)
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 1. УДАЛЯЕМ СТАРЫЕ ЗАПИСИ
            # Если нужно удалить ВООБЩЕ ВСЁ:
            cursor.execute("DELETE FROM `parsed_content`")
            
            # Если нужно удалять только записи с таким же URL (дубликаты):
            # cursor.execute("DELETE FROM `parsed_content` WHERE `url` = %s", (url,))
            
            # 2. ВСТАВЛЯЕМ НОВУЮ ЗАПИСЬ
            sql = """
                INSERT INTO `parsed_content` (`url`, `title`, `price`, `phone`, `content`) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (url, title, price, phone, content))
            
            connection.commit()
            print(f"✅ БД: Таблица очищена, данные записаны: {title}", flush=True)
            return True
    except Exception as e:
        print(f"❌ ОШИБКА БД: {e}", flush=True)
        return False
    finally:
        if connection:
            connection.close()

