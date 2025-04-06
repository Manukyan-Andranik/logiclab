import os

from datetime import datetime
from urllib.parse import quote_plus

from utils import setup_db
USER_NAME = os.getenv('MONGO_USERNAME')
PASSWORD = os.getenv('MONGO_PASSWORD')
escaped_username = quote_plus(USER_NAME)
escaped_password = quote_plus(PASSWORD)
URI = f"mongodb+srv://{escaped_username}:{escaped_password}@cluster0.ckpsnux.mongodb.net/?appName=Cluster0"

# Initialize data if empty
courses_collection, registrations, admins = setup_db(URI)
course = courses_collection.find_one({"_id": "3ds_max"})
print(course)