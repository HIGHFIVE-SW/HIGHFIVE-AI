from typing import Optional, Union, List, Tuple
from mysql.connector import connect, Error, MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from dotenv import load_dotenv
import os

load_dotenv()
# 환경변수로부터 DB 연결 정보 가져오기
DB_HOST = os.getenv("MYSQL_DB_HOST")
DB_NAME = os.getenv("MYSQL_DB_NAME")
DB_USER = os.getenv("MYSQL_DB_USER")
DB_PASSWORD = os.getenv("MYSQL_DB_PASSWORD")

def run_query(query: str, params: Optional[Union[Tuple, List[Tuple]]] = None):
    """
    매번 새로운 MySQL 커넥션을 생성하여 쿼리를 실행하고,
    실행 완료 후 항상 연결을 닫는다.
    """
    conn = None
    cursor = None

    try:
        # 1) 커넥션 생성
        conn = connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        # 2) cursor 생성 (dictionary=True: 결과를 dict 형태로 반환)
        cursor = conn.cursor(dictionary=True)

        # 3) 쿼리 타입 확인
        query_type = query.strip().split()[0].lower()

        # 3) 쿼리 실행
        if query_type == "select": 
            # SELECT 쿼리일 경우
            cursor.execute(query, params)
            return cursor.fetchall()
        elif isinstance(params, list) and all(isinstance(p, tuple) for p in params):
            # 다중 행 처리일 경우
            cursor.executemany(query, params)
        else:
            # 단일 행 실행일 경우
            cursor.execute(query, params)

        conn.commit()
        return cursor.rowcount # 영향받은 행 수 반환

    except Error as e:
        # 에러가 발생하면 적절히 로깅하거나 예외를 재전달할 수 있음
        print(f"MySQL Error: {e}")
        raise

    finally:
        # 4) cursor와 커넥션이 존재하면 반드시 닫는다.
        if cursor:
            try:
                cursor.close()
            except Error as ce:
                print(f"Cursor close error: {ce}")

        if conn:
            try:
                conn.close()
            except Error as se:
                print(f"Connection close error: {se}")
