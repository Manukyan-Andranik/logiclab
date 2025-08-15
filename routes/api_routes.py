from flask import Blueprint, jsonify, request
from datetime import datetime
from extensions import DATA_MANAGER

api_bp = Blueprint('api', __name__)

@api_bp.route('/courses', methods=['GET'])
def api_courses():
    courses_collection = DATA_MANAGER.get_courses()
    courses = list(courses_collection.find({"is_active": True}, {'_id': 0}))
    return jsonify(courses)

@api_bp.route('/register', methods=['POST'])
def api_register():
    courses_collection = DATA_MANAGER.get_courses()
    registrations = DATA_MANAGER.get_registrations()
    data = request.json
    course_id = data.get('course_id')
    
    if not courses_collection.find_one({"_id": course_id, "is_active": True}):
        return jsonify({"error": "Invalid course"}), 400
    
    if registrations.find_one({'email': data['email'], 'course_id': course_id}):
        return jsonify({"error": "Email already registered for this course"}), 400
    
    registration_data = {
        'full_name': data['full_name'],
        'email': data['email'],
        'phone': data['phone'],
        'course_id': course_id,
        'course_title': courses_collection.find_one({"_id": course_id})['title'],
        'registration_date': datetime.now(),
        'status': 'pending'
    }
    
    registrations.insert_one(registration_data)
    return jsonify({"message": "Registration successful"}), 201