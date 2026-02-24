import pymysql

# Настройки подключения к вашей базе host1324224_botanik
DB_CONFIG = {
    'host': 'localhost',
    'user': 'host1324224_botanik',
    'password': 'ВАШ_ПАРОЛЬ_ОТ_БАЗЫ', 
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def save_to_db(url, title, price, phone, content=""):
    """
    Сохраняет данные в БД. 
    Если URL уже есть — обновляет цену и телефон.
    """
    connection = pymysql.connect(**DB_CONFIG)
    try:
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
        print(f"Ошибка БД при сохранении {url}: {e}")
    finally:
        connection.close()

