"""
Database connection management for MySQL / MariaDB using PyMySQL.
Provides connection pooling, request-scoped lifecycle management, and friendly diagnostic errors.
"""
import pymysql
import pymysql.cursors
from flask import g, current_app
from config import Config

def get_db_connection(database_name=None):
    """
    Establish a connection to the MySQL database.
    Returns a PyMySQL Connection with DictCursor.
    """
    db_name = database_name or Config.DB_NAME
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=db_name,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=5,
        )
        return connection
    except pymysql.MySQLError as e:
        # Friendly connection error without exposing sensitive internals
        raise ConnectionError(
            f"Unable to connect to MySQL database '{db_name}' on {Config.DB_HOST}:{Config.DB_PORT}. "
            f"Check that MySQL service is running, credentials in .env are correct, and init_db.py has been executed. "
            f"Details: {str(e)}"
        )

def get_db():
    """
    Get or create a request-scoped database connection stored in Flask 'g'.
    """
    if "db" not in g:
        g.db = get_db_connection()
    return g.db

def close_db(error=None):
    """
    Closes the request-scoped database connection.
    Called automatically on application context teardown.
    """
    db = g.pop("db", None)
    if db is not None:
        try:
            if error:
                db.rollback()
            else:
                db.commit()
        except Exception:
            pass
        finally:
            try:
                db.close()
            except Exception:
                pass

def check_db_health():
    """
    Lightweight health check for MySQL connection and critical tables.
    Returns (status: bool, message: str, details: dict).
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()
            cursor.execute("SHOW TABLES")
            tables = [list(r.values())[0] for r in cursor.fetchall()]
        conn.close()
        return True, "Database connection healthy", {
            "connected": True,
            "host": Config.DB_HOST,
            "database": Config.DB_NAME,
            "tables_found": len(tables),
            "tables": tables,
        }
    except Exception as exc:
        return False, str(exc), {
            "connected": False,
            "host": Config.DB_HOST,
            "database": Config.DB_NAME,
        }
