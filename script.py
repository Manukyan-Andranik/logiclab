import os
import json
from pymongo import MongoClient
import os
import json
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# from urllib.parse import quote_plus
from urllib.parse import quote_plus
from utils import load_env

MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, DEFAULT_INSTRUCTOR_PHOTO = load_env()


USER_NAME = os.getenv('MONGO_USERNAME')
PASSWORD = os.getenv('MONGO_PASSWORD').encode("utf-8")
escaped_username = USER_NAME
escaped_password = quote_plus(PASSWORD)
# -------- CONFIGURATION --------
MONGO_URI = f"mongodb+srv://{escaped_username}:{escaped_password}@cluster0.ckpsnux.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# MONGO_URI = "mongodb+srv://user:password@cluster0.mongodb.net/education_platform"
OUTPUT_DIR = "mongo_exports"  # Directory to save JSON files
DB_NAME = "education_platform"  # Name of your database
# -------------------------------
def export_all_collections(MONGO_URI, DB_NAME, OUTPUT_DIR):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    collections = db.list_collection_names()
    print("Found collections:", collections)

    def convert_types(doc):
        """Recursively convert ObjectId and datetime to strings"""
        if isinstance(doc, dict):
            return {k: convert_types(v) for k, v in doc.items()}
        elif isinstance(doc, list):
            return [convert_types(item) for item in doc]
        elif isinstance(doc, ObjectId):
            return str(doc)
        elif isinstance(doc, datetime):
            return doc.isoformat()
        else:
            return doc

    for collection_name in collections:
        collection = db[collection_name]
        documents = list(collection.find({}))
        # Convert ObjectId and datetime fields
        documents = [convert_types(doc) for doc in documents]

        file_path = os.path.join(OUTPUT_DIR, f"{collection_name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=4)
        print(f"Exported {len(documents)} documents from '{collection_name}' to '{file_path}'")


if __name__ == "__main__":
    export_all_collections(MONGO_URI, DB_NAME, OUTPUT_DIR)
