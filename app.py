import os
from bson import ObjectId
from datetime import datetime
from urllib.parse import quote_plus
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_mail import Mail, Message
from bson import ObjectId
import json

from utils import setup_db, load_env, find_by_id


app = Flask(__name__)
app.secret_key = os.urandom(24)
MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER = load_env()
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

mail = Mail(app)
# app.secret_key = 'your_secret_key_here'
USER_NAME = os.getenv('MONGO_USERNAME')
PASSWORD = os.getenv('MONGO_PASSWORD')
escaped_username = quote_plus(USER_NAME)
escaped_password = quote_plus(PASSWORD)
URI = f"mongodb+srv://{escaped_username}:{escaped_password}@cluster0.ckpsnux.mongodb.net/?appName=Cluster0"

# Initialize data if empty
courses_collection, registrations, admins, instructors_collection = setup_db(URI)

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
    instructors = list(instructors_collection.find())
    instructors = {
        "machine_learning": find_by_id(instructors, "machine_learning_instructor"),
        "3ds_max": find_by_id(instructors, "3ds_max_instructor"),
        }
    print(instructors)
    
    courses = {
        "machine_learning": find_by_id(courses, "machine_learning"),
        "3ds_max": find_by_id(courses, "3ds_max"),
        }
    print(courses)
    return render_template('index.html', courses=courses, instructors=instructors)


# Course route
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
def admin_edit_course(course_id):
    try:
        # Convert to ObjectId if it's a valid string, otherwise use as-is
        if isinstance(course_id, str) and ObjectId.is_valid(course_id):
            course_id_obj = ObjectId(course_id)
        else:
            course_id_obj = course_id
            
        course = courses_collection.find_one({'_id': course_id_obj})
        
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('admin_courses'))
        
        if request.method == 'POST':
            # Validate required fields
            required_fields = ['title', 'duration', 'start_date']
            for field in required_fields:
                if not request.form.get(field):
                    flash(f'{field.capitalize()} is required', 'error')
                    return redirect(url_for('admin_edit_course', course_id=course_id))
            
            try:
                updates = {
                    'title': request.form.get('title'),
                    'duration': request.form.get('duration'),
                    'start_date': request.form.get('start_date'),
                    'schedule': request.form.get('schedule'),
                    'instructor': request.form.get('instructor'),
                    'capacity': int(request.form.get('capacity')) if request.form.get('capacity') else None,
                    'monthly_payment': int(request.form.get('monthly_payment')) if request.form.get('monthly_payment') else None,
                    'total_payment': int(request.form.get('total_payment')) if request.form.get('total_payment') else None,
                    'is_active': request.form.get('is_active') == 'on',
                    'chapters': []
                }

                # Process chapters
                chapter_index = 0
                while f'chapter_{chapter_index}_title' in request.form:
                    chapter_title = request.form.get(f'chapter_{chapter_index}_title')
                    if not chapter_title.strip():
                        chapter_index += 1
                        continue
                        
                    chapter_content = request.form.get(f'chapter_{chapter_index}_content', '')
                    chapter_data = {
                        'title': chapter_title,
                        'content': [line for line in chapter_content.split('\n') if line.strip()],
                        'sections': []
                    }

                    # Process sections
                    section_index = 0
                    while f'chapter_{chapter_index}_section_{section_index}_title' in request.form:
                        section_title = request.form.get(f'chapter_{chapter_index}_section_{section_index}_title')
                        if section_title.strip():  # Only add if title exists
                            try:
                                lessons = json.loads(request.form.get(
                                    f'chapter_{chapter_index}_section_{section_index}_lessons', '[]'))
                            except (json.JSONDecodeError, TypeError):
                                lessons = []
                            
                            section_data = {
                                'section_title': section_title,
                                'lessons': lessons
                            }
                            chapter_data['sections'].append(section_data)
                        section_index += 1

                    updates['chapters'].append(chapter_data)
                    chapter_index += 1
                
                # Update the course
                result = courses_collection.update_one(
                    {'_id': course['_id']},
                    {'$set': updates}
                )
                
                if result.modified_count > 0:
                    flash('Course updated successfully', 'success')
                else:
                    flash('No changes were made', 'info')
                    
                return redirect(url_for('admin_edit_course', course_id=course_id))
                
            except ValueError as e:
                flash(f'Invalid number input: {str(e)}', 'error')
            except Exception as e:
                flash(f'An error occurred: {str(e)}', 'error')
                # Consider logging the actual error for debugging
                # logger.error(f"Error updating course: {str(e)}")
        
        return render_template('admin/edit_course.html', course=course)
        
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('admin_courses'))
@app.route('/admin/students')
@admin_required
def admin_students():
    course_filter = request.args.get('course_id')
    query = {}
    if course_filter:
        query['course_id'] = course_filter
    
    all_students = list(registrations.find(query))
    all_courses = list(courses_collection.find())
    return render_template('admin/students.html', students=all_students, courses=all_courses)

@app.route('/admin/student/<student_id>/update', methods=['POST'])
@admin_required
def admin_update_student(student_id):
    new_status = request.form['status']
    student = registrations.find_one({"_id": ObjectId(student_id)})
    
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('admin_students'))
    
    # Update status in database
    registrations.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"status": new_status}}
    )
    
    # Send email notification
    try:
        send_status_email(student['email'], student['full_name'], student['course_title'], new_status)
        flash('Student status updated and notification sent', 'success')
    except Exception as e:
        app.logger.error(f"Failed to send status email: {str(e)}")
        flash('Status updated but failed to send notification', 'warning')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(url_for('admin_students'))

@app.route('/admin/student/<student_id>/delete', methods=['POST'])
@admin_required
def admin_delete_student(student_id):
    student = registrations.find_one({"_id": ObjectId(student_id)})
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('admin_students'))
    
    registrations.delete_one({"_id": ObjectId(student_id)})
    flash('Student registration deleted successfully', 'success')
    return redirect(url_for('admin_students'))

def send_status_email(to_email, student_name, course_name, new_status):
    subject = f"Your registration status for {course_name} has been updated"
    
    status_messages = {
        'pending': "Your registration is being reviewed.",
        'confirmed': "Your registration has been confirmed! Welcome to the course.",
        'rejected': "We're sorry, but your registration could not be accepted at this time.",
        'completed': "Congratulations on completing the course! Well done!"
    }
    
    body = f"""
    Dear {student_name},
    
    Your registration status for {course_name} has been updated to: {new_status.capitalize()}.
    
    {status_messages.get(new_status, '')}
    
    If you have any questions, please don't hesitate to contact us.
    
    Best regards,
    EduTech Team
    """
    
    msg = Message(
        subject=subject,
        recipients=[to_email],
        body=body
    )
    mail.send(msg)

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

@app.route('/contact', methods=['POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        # Validate input
        if not all([name, email, message]):
            flash('Please fill all fields', 'error')
            return redirect(url_for('home') + '#contact')
        
        try:
            # Send email to admin
            msg = Message(
                subject=f"New message from {name} - EduTech Contact Form",
                recipients=[os.getenv('ADMIN_EMAIL')],
                body=f"""
                Name: {name}
                Email: {email}
                Message: {message}
                
                Sent from EduTech contact form
                """
            )
            mail.send(msg)
            
            # Send confirmation to user
            confirmation_msg = Message(
                subject="Thank you for contacting EduTech",
                recipients=[email],
                body=f"""
                Dear {name},
                
                Thank you for reaching out to us. We have received your message and will get back to you shortly.
                
                Your message:
                {message}
                
                Best regards,
                EduTech Team
                """
            )
            mail.send(confirmation_msg)
            
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            app.logger.error(f"Failed to send email: {str(e)}")
            flash('Failed to send your message. Please try again later.', 'error')
        
        return redirect(url_for('home') + '#contact')

if __name__ == '__main__':
    app.run(host = "0.0.0.0", port=5001,debug=True)