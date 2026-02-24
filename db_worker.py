import os
import pymysql

# Пытаемся взять пароль из секретов GitHub, если не находим — берем локальный
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c') 

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224_botanik',
    'password': DB_PASSWORD, # Используем переменную
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def save_to_db(url, title, price, phone, content=""):
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO `parsed_content` (`url`, `title`, `price`, `phone`, `content`) 
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    `title` = VALUES(`title`),
                    `price` = VALUES(`price`),
                    `phone` = VALUES(`phone`),
                    `content` = VALUES(`content`)
            """
            cursor.execute(sql, (url, title, price, phone, content))
            connection.commit()
    except Exception as e:
        print(f"Ошибка БД: {e}")
    finally:
        if 'connection' in locals():
            connection.close()
