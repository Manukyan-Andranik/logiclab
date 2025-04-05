import os
import hashlib
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

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
    return courses_collection, registrations, admins

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
