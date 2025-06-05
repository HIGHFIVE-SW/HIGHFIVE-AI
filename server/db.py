from mysql.connector import pooling
from dotenv import load_dotenv
import os
load_dotenv()

pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=10,
    pool_reset_session=True,
    host=os.getenv("MYSQL_DB_HOST"),
    database=os.getenv("MYSQL_DB_NAME"),
    user=os.getenv("MYSQL_DB_USER"),
    password=os.getenv("MYSQL_DB_PASSWORD")
)

def run_query(query: str, params=None):
    conn = pool.get_connection()
    cursor = conn.cursor()
    try:
        affected_rows = 0

        # 여러 레코드 삽입인 경우
        if params and isinstance(params, list) and isinstance(params[0], tuple):
            cursor.executemany(query, params)
            affected_rows = cursor.rowcount
        else:
            cursor.execute(query, params)
            affected_rows = cursor.rowcount

        # SELECT 처리
        if query.strip().lower().startswith("select"):
            return cursor.fetchall()
        else:
            conn.commit()
            return affected_rows
    finally:
        cursor.close()
        conn.close()