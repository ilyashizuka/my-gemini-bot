def search_in_db(query):
    # Очищаем запрос
    q = query.lower().replace('?', '').strip()
    # Берем основы слов (минимум 3 символа), например: "лодок" -> "лодк"
    words = [w[:4] for w in q.split() if len(w) >= 3]
    
    if not words:
        return []

    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # Используем OR: найдем всё, где есть хотя бы одно из слов (лодка ИЛИ прокат)
            conditions = " OR ".join(["LOWER(title) LIKE %s OR LOWER(content) LIKE %s" for _ in words])
            params = []
            for w in words:
                params.extend([f'%{w}%', f'%{w}%'])
            
            sql = f"SELECT * FROM parsed_content WHERE {conditions} LIMIT 10"
            cur.execute(sql, params)
            return cur.fetchall()
    except Exception as e:
        print(f"ОШИБКА ПОИСКА: {e}")
        return []
    finally:
        if 'conn' in locals(): conn.close()
