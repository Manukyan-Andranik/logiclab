import os
from bson import ObjectId
from datetime import datetime
from urllib.parse import quote_plus
from flask_mail import Mail, Message
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, current_app

from utils import get_ids, find_by_id, load_env, is_valid_url, generate_download_url
from data_manager import DataManager, admin_required, user_required

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load environment variables
MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, DEFAULT_INSTRUCTOR_PHOTO = load_env()
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

mail = Mail(app)

# MongoDB configuration
USER_NAME = os.getenv('MONGO_USERNAME')
PASSWORD = os.getenv('MONGO_PASSWORD')
escaped_username = quote_plus(USER_NAME)
escaped_password = quote_plus(PASSWORD)
URI = f"mongodb+srv://{escaped_username}:{escaped_password}@cluster0.ckpsnux.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
app.config['MONGO_URI'] = URI

DATA_MANAGER = DataManager(app, URI)

# Site Routes
@app.route('/')
def home():

    courses_collection = DATA_MANAGER.get_courses()
    instructors_collection = DATA_MANAGER.get_instructors()
    visits = DATA_MANAGER.get_visits()
    
    DATA_MANAGER.track_visit(visits)
    courses = list(courses_collection.find({"is_active": True}))
    instructors = list(instructors_collection.find())
    instructor_ids = get_ids(instructors)
    all_instructors = {}
    for id in instructor_ids:
        all_instructors[id] = find_by_id(instructors, id)
        
    course_ids = get_ids(courses)
    all_courses = {}
    for id in course_ids:
        all_courses[id] = find_by_id(courses, id)
    return render_template('index.html', courses=all_courses, instructors=all_instructors)

@app.route('/instructors')
def instructors():
    instructors_collection = DATA_MANAGER.get_instructors()
    visits = DATA_MANAGER.get_visits()
    DATA_MANAGER.track_visit(visits)
    instructors = list(instructors_collection.find())
    instructor_ids = get_ids(instructors)
    all_instructors = {}
    for id in instructor_ids:
        all_instructors[id] = find_by_id(instructors, id)
    return render_template("instructors.html", instructors=all_instructors)

@app.route('/all_courses')
def all_courses():
    courses_collection = DATA_MANAGER.get_courses()
    instructors_collection = DATA_MANAGER.get_instructors()
    visits = DATA_MANAGER.get_visits()
    
    DATA_MANAGER.track_visit(visits)
    courses = list(courses_collection.find({"is_active": True}))
    instructors = list(instructors_collection.find())
    instructor_ids = get_ids(instructors)
    all_instructors = {}
    for id in instructor_ids:
        all_instructors[id] = find_by_id(instructors, id)
        
    course_ids = get_ids(courses)
    all_courses = {}
    for id in course_ids:
        all_courses[id] = find_by_id(courses, id)
        # all_courses[id]["instructor"] = ["vazgen chilanyan", "vazgen ianidnainina"]
        
    return render_template('all_courses.html', courses=all_courses)

@app.route('/course/<course_id>')
def course_details(course_id):
    courses_collection = DATA_MANAGER.get_courses()
    visits = DATA_MANAGER.get_visits()
    DATA_MANAGER.track_visit(visits)
    course = courses_collection.find_one({"_id": course_id})
    if not course:
        return redirect(url_for('home'))
    return render_template('course.html', course=course, course_id=course_id)

@app.route('/register/<course_id>', methods=['GET', 'POST'])
def register(course_id):
    courses_collection = DATA_MANAGER.get_courses()
    registrations = DATA_MANAGER.get_registrations()
    visits = DATA_MANAGER.get_visits()

    DATA_MANAGER.track_visit(visits)
    course = courses_collection.find_one({"_id": course_id})
    if not course:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        age = request.form['age']
        clas = request.form['class']
        convenient_dates = request.form['convenient_dates']
        email = request.form['email']
        phone = request.form['phone']
        computer = request.form.get('computer', 'no')
        
        
        if not all([full_name, email, phone, age, clas]):
            flash('Please fill all fields', 'error')
            return redirect(url_for('register', course_id=course_id))
        
        registrations.insert_one({
            'full_name': full_name,
            'age': age,
            'class': clas,
            'convenient_dates': convenient_dates,
            'computer': computer,
            'email': email,
            'phone': phone,
            'course_id': course_id,
            'course_title': course['title'],
            'registration_date': datetime.now(),
            'status': 'pending'
        })
        
        flash('Գրանցումը հաջողվեց: Մենք շուտով կկապվենք ձեզ հետ', 'success')
    
    return render_template('register.html', course=course, course_id=course_id)

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
                subject=f"New message from {name} - LogicLab Contact Form",
                recipients=[os.getenv('ADMIN_EMAIL')],
                body=f"""
                Name: {name}
                Email: {email}
                Message: {message}
                
                Sent from LogicLab contact form
                """
            )
            mail.send(msg)
            flash('Ձեր հաղորդագրությունը հաջողությամբ ուղարկվել է!', 'success')
            
        except Exception as e:
            app.logger.error(f"Failed to send email: {str(e)}")
            flash('Failed to send your message. Please try again later.', 'error')
        
        return redirect(url_for('home') + '#contact')






# User routes
@app.route('/login', methods=['GET', 'POST'])
def user_login():    
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        decoded_key = DATA_MANAGER._decode_api_key(api_key, expiration_months=13)
        if decoded_key['valid']:
            session['user_logged_in'] = True
            session['api_key'] = api_key
            return redirect(url_for('user_dashboard'))
        flash('Invalid API Key', 'error')
    return render_template('users/login.html')

@app.route('/logout')
def user_logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])
@user_required
def user_dashboard():
    course_id="machine_learning"
    materials = DATA_MANAGER.get_materials()
    all_materials = list(materials.find({"_id": course_id}))
    return render_template('users/profile.html', course_id = course_id, materials=all_materials[0])







# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    admins = DATA_MANAGER.get_admins()
    
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
    courses_collection = DATA_MANAGER.get_courses()
    registrations_collection = DATA_MANAGER.get_registrations()
    
    # Get all courses
    all_courses = list(courses_collection.find())
    
    # Get total students count (count all registrations)
    total_students = registrations_collection.count_documents({})
    
    # Get enrollment counts for each course
    for course in all_courses:
        course_id = course['_id']
        
        # Count students in each status for this course
        course['pending_count'] = registrations_collection.count_documents({
            'course_id': course_id,  # Assuming course_id is stored directly
            'status': 'pending'
        })
        
        course['confirmed_count'] = registrations_collection.count_documents({
            'course_id': course_id,  # Added missing course_id filter
            'status': 'confirmed'
        })
        
        course['rejected_count'] = registrations_collection.count_documents({
            'course_id': course_id,
            'status': 'rejected'
        })
        
        course['completed_count'] = registrations_collection.count_documents({
            'course_id': course_id,
            'status': 'completed'
        })
    
    recent_visitors = list(DATA_MANAGER.get_visits().find().sort('timestamp', -1).limit(5))
    return render_template('admin/dashboard.html', 
                         courses=all_courses,
                         total_students=total_students,
                         recent_visitors=recent_visitors)

# Admin: Courses
@app.route('/admin/courses')
@admin_required
def admin_courses():
    courses_collection = DATA_MANAGER.get_courses()
    all_courses = list(courses_collection.find())
    return render_template('admin/courses.html', courses=all_courses)

@app.route('/admin/courses/edit/<course_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(course_id):
    try:
        courses_collection = DATA_MANAGER.get_courses()
        instructors_collection = DATA_MANAGER.get_instructors()
        
        course = courses_collection.find_one({'_id': course_id})
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('admin_courses'))
        
        instructors = list(instructors_collection.find())
        
        if request.method == 'POST':
            # Validate required fields
            required_fields = {
                'title': 'Course Title',
                'duration': 'Duration',
                'start_date': 'Start Date',
                'schedule': 'Schedule',
                'instructor': 'Instructor',
                'capacity': 'Capacity'
            }
            
            errors = []
            for field, name in required_fields.items():
                if not request.form.get(field):
                    errors.append(f"{name} is required")
            
            if errors:
                flash('Please fix the following errors: ' + ', '.join(errors), 'error')
                return redirect(url_for('admin_edit_course', course_id=course_id))
            
            try:
                updates = {
                    'title': request.form.get('title'),
                    'icon_url': request.form.get('icon_url'),
                    'duration': request.form.get('duration'),
                    'start_date': request.form.get('start_date'),
                    'schedule': request.form.get('schedule'),
                    'instructor': request.form.getlist('instructor'),
                    'capacity': int(request.form.get('capacity')),
                    'monthly_payment': int(request.form.get('monthly_payment', 0)) if request.form.get('monthly_payment') else None,
                    'total_payment': int(request.form.get('total_payment', 0)) if request.form.get('total_payment') else None,
                    'is_active': request.form.get('is_active') == 'on',
                    'curriculum': request.form.get('curriculum', ''),
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
                        'content': [line.strip() for line in chapter_content.split('\n') if line.strip()],
                    }
                    updates['chapters'].append(chapter_data)
                    chapter_index += 1
                
                # Update the course
                result = courses_collection.update_one(
                    {'_id': course['_id']},
                    {'$set': updates}
                )
                
                flash('Course updated successfully', 'success')
                return redirect(url_for('admin_edit_course', course_id=course_id))
                
            except ValueError as e:
                flash(f'Invalid number input: {str(e)}', 'error')
            except Exception as e:
                flash(f'An error occurred: {str(e)}', 'error')
        
        return render_template('admin/edit_course.html', course=course, instructors=instructors)
        
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('admin_courses'))
    
@app.route('/admin/courses/delete/<course_id>', methods=['POST'])
@admin_required
def admin_delete_course(course_id):
    courses_collection = DATA_MANAGER.get_courses()
    registrations = DATA_MANAGER.get_registrations()
    
    try:
        student_count = registrations.count_documents({"course_id": course_id})
        if student_count > 0:
            flash('Cannot delete course with registered students', 'error')
            return redirect(url_for('admin_courses'))

        result = courses_collection.delete_one({"_id": course_id})
        if result.deleted_count == 1:
            flash('Course deleted successfully', 'success')
        else:
            flash('Course not found', 'error')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
    
    return redirect(url_for('admin_courses'))

# Admin: Instructors
@app.route('/admin/instructors')
@admin_required
def admin_instructors():
    instructors_collection = DATA_MANAGER.get_instructors()
    all_instructors = list(instructors_collection.find())
    return render_template('admin/instructors.html', instructors=all_instructors)

@app.route('/admin/instructors/add', methods=['GET', 'POST'])
@admin_required
def admin_add_instructor():
    instructors_collection = DATA_MANAGER.get_instructors()
    if request.method == 'POST':
        try:
            # Validate required fields
            required_fields = ['firstName', 'lastName', 'profession', 'specialization', 
                             'workExperience', 'education_institution', 'education_degree',
                             'education_fieldOfStudy', 'contact_phone']
            
            for field in required_fields:
                if not request.form.get(field):
                    flash(f'{" ".join(field.split("_")).capitalize()} is required', 'error')
                    return redirect(url_for('admin_add_instructor'))

           # First, extract companies dynamically
            companies = []
            i = 0
            while True:
                name = request.form.get(f'company_{i}_name')
                company_type = request.form.get(f'company_{i}_type')
                role = request.form.get(f'company_{i}_role')
                
                # Break the loop if name is not provided (assuming name is required)
                if not name:
                    break

                companies.append({
                    'company': name,
                    'type': company_type,
                    'role': role
                })
                i += 1
            # Now construct the instructor object
            new_instructor = {
                '_id': f"{request.form.get('specialization').lower().replace(' ', '_')}_instructor",
                'photo': request.form.get('photo', 'default_instructor.jpg'),
                'firstName': request.form.get('firstName'),
                'lastName': request.form.get('lastName'),
                'education': {
                    'institution': request.form.get('education_institution'),
                    'degree': request.form.get('education_degree'),
                    'fieldOfStudy': request.form.get('education_fieldOfStudy')
                },
                'profession': request.form.get('profession'),
                'specialization': request.form.get('specialization'),
                'workExperience': int(request.form.get('workExperience')),
                'companies': companies,
                'contacts': {
                    'phone': request.form.get('contact_phone'),
                    'linkedin': request.form.get('contact_linkedin', ''),
                    'web': request.form.get('contact_web', '')
                },
                'skills': [skill.strip() for skill in request.form.get('skills', '').split(',') if skill.strip()],
                'softwareProficiency': [software.strip() for software in request.form.get('softwareProficiency', '').split(',') if software.strip()]
            }

            # Insert the new instructor
            instructors_collection.insert_one(new_instructor)
            flash('Instructor added successfully', 'success')
            return redirect(url_for('admin_instructors'))
            
        except ValueError as e:
            flash(f'Invalid number input: {str(e)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('admin/add_instructor.html')

@app.route('/admin/instructors/edit/<instructor_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_instructor(instructor_id):
    instructors_collection = DATA_MANAGER.get_instructors()
    
    instructor = instructors_collection.find_one({"_id": instructor_id})
    if not instructor:
        flash('Instructor not found', 'error')
        return redirect(url_for('admin_instructors'))

    if request.method == 'POST':
        try:
            companies = []
            i = 0
            while f'company_{i}_name' in request.form:
                company = {
                    'company': request.form.get(f'company_{i}_name'),
                    'type': request.form.get(f'company_{i}_type'),
                    'role': request.form.get(f'company_{i}_role')
                }
                companies.append(company)
                i += 1

            # Save to instructor object
            instructor['companies'] = companies
            photo_url = request.form.get('photo_url')
            photo_url = photo_url if is_valid_url(photo_url) else DEFAULT_INSTRUCTOR_PHOTO
            # Basic info
            updates = {
                "firstName": request.form.get("firstName"),
                "lastName": request.form.get("lastName"),
                "profession": request.form.get("profession"),
                "specialization": request.form.get("specialization"),
                "workExperience": int(request.form.get("workExperience", 0)),
                "photo_url": photo_url,    
                "education": {
                    "institution": request.form.get("education_institution"),
                    "degree": request.form.get("education_degree"),
                    "fieldOfStudy": request.form.get("education_fieldOfStudy")
                },
                "contacts": {
                    "phone": request.form.get("contact_phone"),
                    "linkedin": request.form.get("contact_linkedin"),
                    "web": request.form.get("contact_web")
                },
                'companies': companies,
            }
            # Process skills
            skills = request.form.get("skills", "")
            updates["skills"] = [skill.strip() for skill in skills.split(",") if skill.strip()]

            # Process software
            software = request.form.get("softwareProficiency", "")
            updates["softwareProficiency"] = [s.strip() for s in software.split(",") if s.strip()]

            # Update the instructor
            instructors_collection.update_one(
                {"_id": instructor_id},
                {"$set": updates}
            )
            flash('Instructor updated successfully', 'success')
            return redirect(url_for('admin_edit_instructor', instructor_id=instructor_id))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    return render_template('admin/edit_instructor.html', instructor=instructor)

@app.route('/admin/instructors/delete/<instructor_id>', methods=['POST'])
@admin_required
def admin_delete_instructor(instructor_id):
    courses_collection = DATA_MANAGER.get_courses()
    instructors_collection = DATA_MANAGER.get_instructors()
    
    try:
        course_count = courses_collection.count_documents({
            "instructor": {"$regex": instructor_id.split('_')[0], "$options": "i"}
        })
        
        if course_count > 0:
            flash('Cannot delete instructor assigned to courses', 'error')
            return redirect(url_for('admin_instructors'))

        result = instructors_collection.delete_one({"_id": instructor_id})
        if result.deleted_count == 1:
            flash('Instructor deleted successfully', 'success')
        else:
            flash('Instructor not found', 'error')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
    
    return redirect(url_for('admin_instructors'))

# Admin: Students
@app.route('/admin/students')
@admin_required
def admin_students():
    courses_collection = DATA_MANAGER.get_courses()
    registrations = DATA_MANAGER.get_registrations()
    course_filter = request.args.get('course_id')
    query = {}
    if course_filter:
        query['course_id'] = course_filter
    
    all_students = list(registrations.find(query))
    all_courses = list(courses_collection.find())
    return render_template('admin/students.html', students=all_students, courses=all_courses)

@app.route('/admin/student/<student_id>/delete', methods=['POST'])
@admin_required
def admin_delete_student(student_id):
    registrations = DATA_MANAGER.get_registrations()
    student = registrations.find_one({"_id": ObjectId(student_id)})
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('admin_students'))
    
    registrations.delete_one({"_id": ObjectId(student_id)})
    flash('Student registration deleted successfully', 'success')
    return redirect(url_for('admin_students'))


@app.route('/admin/student/<student_id>/update', methods=['POST'])
@admin_required
def admin_update_student(student_id):
    registrations = DATA_MANAGER.get_registrations()
    new_status = request.form['status']
    student = registrations.find_one({"_id": ObjectId(student_id)})
    
    if not student:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        flash('Student not found', 'error')
        return redirect(url_for('admin_students'))
    
    # Update status in database
    registrations.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"status": new_status}}
    )
    
    # Send email notification
    email_sent = DATA_MANAGER.send_status_email(
        mail,
        student['email'], 
        student['full_name'], 
        student['course_title'], 
        new_status
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'email_sent': email_sent,
            'new_status': new_status
        })
    
    if email_sent:
        flash('Student status updated and notification sent', 'success')
    else:
        flash('Status updated but failed to send notification', 'warning')
    
    return redirect(url_for('admin_students'))

@app.route('/admin/courses/add', methods=['GET', 'POST'])
@admin_required
def admin_add_course():
    courses_collection = DATA_MANAGER.get_courses()
    instructors_collection = DATA_MANAGER.get_instructors()
    if request.method == 'POST':
        try:
            # Validate required fields
            required_fields = ['course_id', 'title', 'duration', 'start_date', 'schedule', 
                             'instructor', 'capacity', 'monthly_payment', 'total_payment']
            for field in required_fields:
                if not request.form.get(field):
                    flash(f'{field.replace("_", " ").capitalize()} is required', 'error')
                    return redirect(url_for('admin_add_course'))

            # Process chapters
            chapters = []
            chapter_index = 0
            while True:
                chapter_title = request.form.get(f'chapter_{chapter_index}_title')
                if not chapter_title:
                    break
                
                chapter_content = request.form.get(f'chapter_{chapter_index}_content', '')
                lessons = [line.strip() for line in chapter_content.split('\n') if line.strip()]
                
                chapters.append({
                    'title': chapter_title,
                    'content': lessons
                })
                chapter_index += 1

            if not chapters:
                flash('At least one chapter is required', 'error')
                return redirect(url_for('admin_add_course'))

            new_course = {
                '_id': request.form['course_id'].lower().replace(' ', '_'),
                'title': request.form['title'],
                'portfolio': request.form['portfolio'],
                'duration': request.form['duration'],
                'start_date': request.form['start_date'],
                'schedule': request.form['schedule'],
                'instructor': request.form['instructor'],
                'capacity': int(request.form['capacity']),
                'monthly_payment': int(request.form['monthly_payment']),
                'total_payment': int(request.form['total_payment']),
                'is_active': request.form.get('is_active') == 'on',
                'chapters': chapters
            }

            # Check if course ID already exists
            if courses_collection.find_one({'_id': new_course['_id']}):
                flash('Course ID already exists', 'error')
                return redirect(url_for('admin_add_course'))

            # Insert the new course
            courses_collection.insert_one(new_course)
            flash('Course added successfully', 'success')
            return redirect(url_for('admin_courses'))
            
        except ValueError as e:
            flash(f'Invalid number input: {str(e)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('admin_add_course'))
    
    instructors = list(instructors_collection.find())
    return render_template('admin/add_course.html', instructors=instructors)

# Admin: Visitors
@app.route('/admin/visitors')
@admin_required
def admin_visitors():
    visits = DATA_MANAGER.get_visits()
    # Add to your aggregation pipeline
    country_stats = list(visits.aggregate([
        {"$match": {"geo.country": {"$exists": True}}},
        {
            "$group": {
                "_id": "$geo.country",
                "count": {"$sum": 1},
                "code": {"$first": "$geo.country_code"}
            }
        },
        {"$sort": {"count": -1}}
    ]))
    
    # Get visitor statistics
    pipeline = [
        {
            "$group": {
                "_id": "$ip_address",
                "total_visits": {"$sum": 1},
                "last_visit": {"$max": "$timestamp"},
                "first_visit": {"$min": "$timestamp"},
                "browser": {"$last": "$browser"},
                "os": {"$last": "$os"},
                "device": {"$last": "$device"},
                "is_bot": {"$last": "$is_bot"}
            }
        },
        {"$sort": {"last_visit": -1}}
    ]
    
    visitors = list(visits.aggregate(pipeline))
    
    # Get daily visit counts
    daily_pipeline = [
        {
            "$group": {
                "_id": "$date",
                "visits": {"$sum": 1},
                "unique_visitors": {"$addToSet": "$ip_address"}
            }
        },
        {
            "$project": {
                "date": "$_id",
                "visits": 1,
                "unique_visitors": {"$size": "$unique_visitors"},
                "_id": 0
            }
        },
        {"$sort": {"date": -1}}
    ]
    
    daily_stats = list(visits.aggregate(daily_pipeline))
    
    # Get device statistics
    device_stats = list(visits.aggregate([
        {
            "$group": {
                "_id": "$device",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}}
    ]))
    
    # Get browser statistics
    browser_stats = list(visits.aggregate([
        {
            "$group": {
                "_id": "$browser",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}}
    ]))
    
    # Get OS statistics
    os_stats = list(visits.aggregate([
        {
            "$group": {
                "_id": "$os",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}}
    ]))
    
    return render_template('admin/visitors.html', 
                         visitors=visitors, 
                         daily_stats=daily_stats,
                         device_stats=device_stats,
                         browser_stats=browser_stats,
                         os_stats=os_stats,
                         total_visits=visits.count_documents({}),
                         unique_visitors=len(visitors))

@app.route('/admin/visitors/<ip>')
@admin_required
def admin_visitor_details(ip):
    visits = DATA_MANAGER.get_visits()
    
    # Get all visits from this IP
    visitor_visits = list(visits.find({"ip_address": ip}).sort("timestamp", -1))
    
    if not visitor_visits:
        flash('No visits found for this IP address', 'error')
        return redirect(url_for('admin_visitors'))
    
    # Get first and last visit
    first_visit = visitor_visits[-1]
    last_visit = visitor_visits[0]
    
    # Get browser and device info from last visit
    browser = last_visit.get('browser', 'Unknown')
    os = last_visit.get('os', 'Unknown')
    device = last_visit.get('device', 'Unknown')
    
    return render_template('admin/visitor_details.html',
                         ip=ip,
                         visits=visitor_visits,
                         total_visits=len(visitor_visits),
                         first_visit=first_visit,
                         last_visit=last_visit,
                         browser=browser,
                         os=os,
                         device=device)

# Admin: Materials

@app.route('/admin/materials')
def admin_materials():
    # try:
    # Get all courses and materials counts
    courses = DATA_MANAGER.get_courses()
    all_courses = list(courses.find({"is_active": True}))
    selected_course_id = "machine_learning" # request.args.get('course', '')
    materials = DATA_MANAGER.get_materials()
    all_materials = list(materials.find({"_id": selected_course_id}))
    
    return render_template('admin/materials.html',
                        all_courses=all_courses,
                        selected_course=all_courses[0],
                        materials=all_materials if all_materials else {'materials': []})
    
    # except Exception as e:
    #     current_app.logger.error(f"Error in admin_materials: {str(e)}")
    #     flash('An error occurred while loading materials', 'error')
    #     return redirect(url_for('admin_dashboard'))

@app.route('/admin/materials/<course_id>')
def admin_material_details(course_id):
    try:
        materials = DATA_MANAGER.get_materials_by_course_id(course_id=course_id)
        
        if not materials:
            materials = [{'name': 'New Course', 'materials': {}}]
        
        return render_template('admin/material_details.html',
                            selected_course=course_id,
                            materials=materials[0])
    
    except Exception as e:
        current_app.logger.error(f"Error in admin_material_details: {str(e)}")
        flash('An error occurred while loading materials', 'error')
        return redirect(url_for('admin_materials'))

@app.route('/admin/materials/delete', methods=['POST'])
def delete_lesson():
    try:
        data = request.get_json()
        course_id = data['course_id']
        lesson_key = data['lesson_key']
        
        success = DATA_MANAGER.delete_lesson(course_id, lesson_key)
        
        return jsonify({
            'success': success,
            'message': 'Lesson deleted successfully' if success else 'Failed to delete lesson'
        })
    
    except Exception as e:
        current_app.logger.error(f"Error deleting lesson: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/admin/materials/add', methods=['POST'])
def add_material():
    try:
        course_id = request.form.get('course_id')
        name = request.form.get('name')
        google_drive_url = request.form.get('google_drive_url')
        
        if not all([course_id, name, google_drive_url]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin_materials', course=course_id))
        
        material_data = {
            "name": name.strip(),
            "google_drive_url": google_drive_url.strip(),
            "download_url": generate_download_url(google_drive_url)
        }
        
        if DATA_MANAGER.add_material(course_id, material_data):
            flash('Material added successfully!', 'success')
        else:
            flash('Failed to add material', 'error')
            
        return redirect(url_for('admin_materials', course=course_id))
    
    except Exception as e:

        current_app.logger.error(f"Error adding material: {str(e)}")
        flash('An error occurred while adding the material', 'error')
        return redirect(url_for('admin_materials'))

@app.route('/admin/materials/update', methods=['POST'])
def update_materials():
    try:
        data = request.get_json()
        course_id = data['course_id']
        lesson_key = data['lesson_key']
        updated_data = data['updated_data']
        success = DATA_MANAGER.update_material(course_id, lesson_key, updated_data)
        
        return jsonify({
            'success': success,
            'message': 'Materials updated successfully' if success else 'Failed to update materials'
        })
    
    except Exception as e:
        current_app.logger.error(f"Error updating materials: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/admin/materials/add_lesson', methods=['POST'])
def add_lesson():
    try:
        if request.is_json:
            data = request.get_json()
            course_id = data.get('course_id')
            lesson_key = data.get('lesson_key')
            lesson_data = data.get('lesson_data')
        else:
            course_id = request.form.get('course_id')
            lesson_key = request.form.get('lesson_key')
            lesson_data = {
                'tittle': request.form.get('title'),
                'presentations': [url.strip() for url in request.form.getlist('presentations[]') if url.strip()],
                'code': [url.strip() for url in request.form.getlist('code[]') if url.strip()],
                'other': [url.strip() for url in request.form.getlist('other[]') if url.strip()]
            }

        message, msg_type = DATA_MANAGER.add_material(course_id, lesson_key, lesson_data)

        if request.is_json:
            return jsonify({
                'success': msg_type == 'success',
                'message': message
            })

        flash(message, msg_type)
        return redirect(url_for('admin_materials'))

    except Exception as e:
        error_message = f"Error adding lesson: {str(e)}"
        current_app.logger.error(error_message)
        if request.is_json:
            return jsonify({'success': False, 'message': error_message}), 500
        else:
            flash('An error occurred while adding the lesson', 'error')
            return redirect(url_for('admin_materials'))


# API Endpoints
@app.route('/api/courses', methods=['GET'])
def api_courses():
    courses_collection = DATA_MANAGER.get_courses()
    courses = list(courses_collection.find({"is_active": True}, {'_id': 0}))
    return jsonify(courses)

@app.route('/api/register', methods=['POST'])
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

@app.route('/api/materials')
@user_required
def get_all_materials():
    try:
        # Get all course materials
        materials = {
            "machine_learning": DATA_MANAGER.get_materials_by_course_id("machine_learning")[0],
            "ai_tools": DATA_MANAGER.get_materials_by_course_id("ai_tools")[0],
            "3d_modeling": DATA_MANAGER.get_materials_by_course_id("3d_modeling")[0],
            "photography": DATA_MANAGER.get_materials_by_course_id("photography")[0]
        }
        return jsonify(materials)
    except Exception as e:
        current_app.logger.error(f"Error getting all materials: {str(e)}")
        return jsonify({"error": "Failed to load materials"}), 500
    
if __name__ == '__main__':
    app.run(host = "0.0.0.0", port=5001, debug=True)