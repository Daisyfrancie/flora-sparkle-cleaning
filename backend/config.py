import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-this-secret-key')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
DATABASE_URL = os.getenv('DATABASE_URL')

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'flora_sparkle_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
}
