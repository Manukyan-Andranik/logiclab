import os
import hashlib
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from urllib.parse import quote_plus
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

#   Dotenv setup
dotenv_path = ".env"
load_dotenv(dotenv_path=dotenv_path)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# app.secret_key = 'your_secret_key_here'
USER_NAME = os.getenv('MONGO_USERNAME')
PASSWORD = os.getenv('MONGO_PASSWORD')
escaped_username = quote_plus(USER_NAME)
escaped_password = quote_plus(PASSWORD)
uri = f"mongodb+srv://{escaped_username}:{escaped_password}@cluster0.ckpsnux.mongodb.net/?appName=Cluster0"

# MongoDB Connection
client = MongoClient(uri)
db = client.education_platform
courses_collection = db.courses
registrations = db.registrations
admins = db.admins

# Generate a secure API key (run once to create admin)
def generate_api_key():
    return hashlib.sha256(os.urandom(32)).hexdigest()

# Initialize data if empty
if courses_collection.count_documents({}) == 0:
    courses_collection.insert_many([

    ])

# Create admin if not exists (run once)
if admins.count_documents({}) == 0:
    api_key = generate_api_key()
    admins.insert_one({
        "username": "admin",
        "api_key": api_key,
        "created_at": datetime.now()
    })

# Admin authentication decorator
def admin_required(f):
    def wrapper(*args, **kwargs):
        if 'admin_logged_in' not in session:
            provided_key = request.args.get('api_key') or request.form.get('api_key')
            if not provided_key:
                return redirect(url_for('admin_login'))
            
            admin = admins.find_one({"api_key": provided_key})
            if not admin:
                flash('Invalid API key', 'error')
                return redirect(url_for('admin_login'))
            
            session['admin_logged_in'] = True
            session['api_key'] = provided_key
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
def home():
    courses = list(courses_collection.find({"is_active": True}))
    courses = {
        "machine_learning": courses[0],
        "3ds_max": courses[1],
        }

    return render_template('index.html', courses=courses)

@app.route('/course/<course_id>')
def course_details(course_id):
    course = courses_collection.find_one({"_id": course_id})
    if not course:
        return redirect(url_for('home'))
    return render_template('course.html', course=course, course_id=course_id)

@app.route('/register/<course_id>', methods=['GET', 'POST'])
def register(course_id):
    course = courses_collection.find_one({"_id": course_id})
    if not course:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        
        if not all([full_name, email, phone]):
            flash('Please fill all fields', 'error')
            return redirect(url_for('register', course_id=course_id))
        
        if registrations.find_one({'email': email, 'course_id': course_id}):
            flash('This email is already registered for the course', 'error')
            return redirect(url_for('register', course_id=course_id))
        
        registrations.insert_one({
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'course_id': course_id,
            'course_title': course['title'],
            'registration_date': datetime.now(),
            'status': 'pending'
        })
        
        flash('Registration successful! We will contact you soon.', 'success')
        return redirect(url_for('course_details', course_id=course_id))
    
    return render_template('register.html', course=course, course_id=course_id)

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        admin = admins.find_one({"api_key": api_key})
        if admin:
            session['admin_logged_in'] = True
            session['api_key'] = api_key
            return redirect(url_for('admin_dashboard'))
        flash('Invalid API Key', 'error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    return redirect(url_for('admin_courses'))

@app.route('/admin/courses')
@admin_required
def admin_courses():
    all_courses = list(courses_collection.find())
    return render_template('admin/courses.html', courses=all_courses)

@app.route('/admin/courses/edit/<course_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(course_id):
    course = courses_collection.find_one({"_id": course_id})
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    if request.method == 'POST':
        update_data = {
            "title": request.form['title'],
            "duration": request.form['duration'],
            "start_date": request.form['start_date'],
            "schedule": request.form['schedule'],
            "description": request.form['description'],
            "price": float(request.form['price']),
            "instructor": request.form['instructor'],
            "capacity": int(request.form['capacity']),
            "is_active": request.form.get('is_active') == 'on'
        }
        
        courses_collection.update_one(
            {"_id": course_id},
            {"$set": update_data}
        )
        flash('Course updated successfully', 'success')
        return redirect(url_for('admin_courses'))
    
    return render_template('admin/edit_course.html', course=course)

@app.route('/admin/students')
@admin_required
def admin_students():
    course_filter = request.args.get('course_id')
    query = {}
    if course_filter:
        query['course_id'] = course_filter
    
    all_students = list(registrations.find(query))
    all_courses = list(courses_collection.find())
    print(all_courses)
    return render_template('admin/students.html', students=all_students, courses=all_courses)

@app.route('/admin/student/<student_id>/update', methods=['POST'])
@admin_required
def admin_update_student(student_id):
    new_status = request.form['status']
    registrations.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"status": new_status}}
    )
    flash('Student status updated', 'success')
    return redirect(url_for('admin_students'))

# API Endpoints
@app.route('/api/courses', methods=['GET'])
def api_courses():
    courses = list(courses_collection.find({"is_active": True}, {'_id': 0}))
    return jsonify(courses)

@app.route('/api/register', methods=['POST'])
def api_register():
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

if __name__ == '__main__':
    app.run(debug=True)