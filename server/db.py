from typing import Optional

from mysql.connector import pooling
from mysql.connector.cursor import MySQLCursorDict
from mysql.connector.pooling import PooledMySQLConnection
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

def run_query(query: str, params:Optional[tuple]=None):
    conn: PooledMySQLConnection = pool.get_connection()
    cursor: MySQLCursorDict  = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()  # 풀로 반환
    return results
