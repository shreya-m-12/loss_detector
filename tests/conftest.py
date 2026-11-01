"""
PyTest configuration and fixtures for Business Loss Detection System.
Provides isolated test database fixtures and Flask test client.
"""
import os
import pytest
import pymysql
from app import create_app
from config import Config
from init_db import init_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes the isolated test database once per test session."""
    init_database(Config.TEST_DB_NAME)
    yield

@pytest.fixture
def app(setup_test_db):
    """Creates a test Flask app configured to use the test database with CSRF disabled for tests."""
    app_instance = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "DB_NAME": Config.TEST_DB_NAME,
    })
    return app_instance

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def test_db_conn():
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.TEST_DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    yield conn
    conn.close()
