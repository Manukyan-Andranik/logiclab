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

def setup_db(uri):
    # MongoDB Connection
    client = MongoClient(uri)
    db = client.education_platform
    courses_collection = db.courses
    registrations = db.registrations
    admins = db.admins
    instructors = db.instructors
    return courses_collection, registrations, admins, instructors

def chack_db(courses_collection, registrations, admins):
    if courses_collection.count_documents({}) == 0:
        courses_collection.insert_many([]) 

    # Create admin if not exists (run once)
    if admins.count_documents({}) == 0:
        api_key = generate_api_key()
        admins.insert_one({
            "username": "admin",
            "api_key": api_key,
            "created_at": datetime.now()
        })

def find_by_id(data_list, target_id):
    """
    Find the first dictionary in the list where '_id' matches the target_id.

    Parameters:
        data_list (list): A list of dictionaries.
        target_id (str): The value to search for in the '_id' field.

    Returns:
        dict or None: The matched dictionary or None if not found.
    """
    return next((item for item in data_list if item.get("_id") == target_id), None)

def get_ids(data_list):
    res = [item.get("_id") for item in data_list]
    return res

def update_course_document(course_data, mongo_uri, db_name, collection_name):
    """
    Updates a course document in MongoDB based on its _id field.

    :param course_data: dict, the full course JSON with the "_id" key
    :param mongo_uri: str, MongoDB URI connection string
    :param db_name: str, database name
    :param collection_name: str, collection name
    """
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]

    # Ensure "_id" exists
    if "_id" not in course_data:
        raise ValueError("The provided data must contain an '_id' field.")

    # Perform the update
    result = collection.update_one(
        {"_id": course_data["_id"]},
        {"$set": course_data},
        upsert=True  # Set to True if you want to insert if not found
    )

    # Feedback
    if result.matched_count > 0:
        print(f"Document with _id '{course_data['_id']}' successfully updated.")
    elif result.upserted_id:
        print(f"Document with _id '{course_data['_id']}' was not found and has been inserted.")
    else:
        print(f"No changes made to the document with _id '{course_data['_id']}'.")

    # Close connection
    client.close()
