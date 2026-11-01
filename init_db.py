"""
Database initialization script for Business Loss Detection System.
Creates the database if missing, executes schema.sql, and seeds the default business.
Safe to re-run anytime (idempotent).
"""
import os
import sys
import pymysql
from config import Config

def init_database(target_db=None):
    db_name = target_db or Config.DB_NAME
    print(f"[init_db] Initializing database '{db_name}' on {Config.DB_HOST}:{Config.DB_PORT}...")

    # Step 1: Connect to MySQL server without selecting database to ensure DB exists
    try:
        server_conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
        )
    except pymysql.MySQLError as err:
        print(f"[init_db ERROR] Failed to connect to MySQL server: {err}")
        print("Please check that MySQL service is running and credentials in .env are correct.")
        sys.exit(1)

    try:
        with server_conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            print(f"[init_db] Database '{db_name}' verified/created.")
    finally:
        server_conn.close()

    # Step 2: Connect to the specific database and execute schema.sql
    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
    if not os.path.isfile(schema_path):
        print(f"[init_db ERROR] schema.sql not found at {schema_path}")
        sys.exit(1)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    db_conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=db_name,
        charset="utf8mb4",
        autocommit=False,
    )

    try:
        with db_conn.cursor() as cursor:
            # Execute statement by statement
            statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
            for stmt in statements:
                cursor.execute(stmt)

            # Seed default single-user business if not present
            cursor.execute(
                """
                INSERT INTO businesses (business_id, business_name)
                VALUES (1, 'Corner Store Mart')
                ON DUPLICATE KEY UPDATE business_name = VALUES(business_name)
                """
            )
            db_conn.commit()
            print(f"[init_db] All tables successfully created and default business seeded in '{db_name}'.")
    except Exception as exc:
        db_conn.rollback()
        print(f"[init_db ERROR] Error applying schema: {exc}")
        sys.exit(1)
    finally:
        db_conn.close()

if __name__ == "__main__":
    target = Config.TEST_DB_NAME if "--test" in sys.argv else Config.DB_NAME
    init_database(target)
