import pymysql
from pymysql.cursors import DictCursor

from app.config import (
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)


def mysql_configured() -> bool:
    return bool(MYSQL_USER and MYSQL_DATABASE)


def get_connection():
    if not mysql_configured():
        raise RuntimeError("MySQL no configurado (MYSQL_USER y MYSQL_DATABASE requeridos)")
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )
