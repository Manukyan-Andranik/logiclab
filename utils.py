import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(dotenv_path=".env")

def load_env():
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    return MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER

def generate_api_key():
    return hashlib.sha256(os.urandom(32)).hexdigest()

def find_by_id(data_list, target_id):
    return next((item for item in data_list if item.get("_id") == target_id), None)

def get_ids(data_list):
    return [item.get("_id") for item in data_list]

def check_db(uri):
    """Initialize database with sample data if empty"""
    client = MongoClient(uri)
    db = client.education_platform
    
    # Create admin if not exists
    if db.admins.count_documents({}) == 0:
        api_key = generate_api_key()
        db.admins.insert_one({
            "username": "admin",
            "api_key": api_key,
            "created_at": datetime.now()
        })
    
    client.close()