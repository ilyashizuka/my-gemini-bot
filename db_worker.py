import pymysql

# Настройки подключения
DB_CONFIG = {
    'host': 'localhost',
    'user': 'host1324224_botanik',
    'password': 'ВАШ_ПАРОЛЬ',
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def save_to_db(url, title, content):
    """Сохраняет данные или обновляет их, если URL уже существует"""
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            sql = """INSERT INTO `parsed_content` (`url`, `title`, `content`) 
                     VALUES (%s, %s, %s)
                     ON DUPLICATE KEY UPDATE `title`=%s, `content`=%s"""
            cursor.execute(sql, (url, title, content, title, content))
            connection.commit()
    finally:
        connection.close()
