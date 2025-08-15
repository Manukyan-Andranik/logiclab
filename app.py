import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_mail import Mail, Message
from sqlalchemy.exc import IntegrityError
from data_manager import DataManager  # Assuming you have a data_manager module for handling data operations
from extensions import db  # single shared db instance
from tables import Course, CourseChapter, Student, Instructor, InstructorCompany, Visitor
from utils import load_env


def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # Load environment variables
    MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, DEFAULT_INSTRUCTOR_PHOTO = load_env()
    mail = Mail()   
    app.config.update(
        MAIL_SERVER=MAIL_SERVER,
        MAIL_PORT=MAIL_PORT,
        MAIL_USE_TLS=MAIL_USE_TLS,
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_DEFAULT_SENDER=MAIL_DEFAULT_SENDER,
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "postgresql://logicdb@localhost/logicdb"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # Initialize extensions
    mail.init_app(app)
    db.init_app(app)
    return app


app = create_app()

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/instructors')
def instructors():
    instructors = Instructor.query.all()
    instructors_dict = {}

    for instructor in instructors:
        # Collect all associated companies
        companies = [
            {
                "name": company.company,
                "type": company.type,
                "role": company.role
            }
            for company in instructor.companies
        ]

        instructors_dict[instructor.instructor_id] = {
            "firstName": instructor.first_name,
            "lastName": instructor.last_name,
            "specialization": instructor.specialization,
            "profession": instructor.profession,
            "workExperience": instructor.work_experience,
            "skills": instructor.skills,
            "softwareProficiency": instructor.software_proficiency,
            "phone": instructor.phone,
            "linkedin": instructor.linkedin,
            "education": {
                "institution": instructor.institution,
                "degree": instructor.degree,
                "fieldOfStudy": instructor.field_of_study
            },
            "contacts": {
            "phone": instructor.phone,
            "linkedin": instructor.linkedin,
            "web": instructor.web
            },
            "web": instructor.web,
            "photo_url": instructor.photo_url or os.getenv("DEFAULT_INSTRUCTOR_PHOTO"),
            "institution": instructor.institution,
            "degree": instructor.degree,
            "fieldOfStudy": instructor.field_of_study,
            "companies": companies,
        }

    return render_template("instructors.html", instructors=instructors_dict)

@app.route('/all_courses')
def all_courses():
    courses = Course.query.filter_by(is_active=True).all()
    print(courses)
    courses_dict = {}
    for course in courses:
        courses_dict[course.course_id] = {
            "title": course.title,
            "duration": course.duration,
            "start_date": course.start_date.isoformat() if course.start_date else None,
            "schedule": course.schedule,
            "instructors": [instructor for instructor in course.instructors],
            "capacity": course.capacity,
            "monthly_payment": course.monthly_payment,
            "total_payment": course.total_payment,
            "is_active": course.is_active,
            "portfolio": course.portfolio,
            "curriculum": course.curriculum,
            "icon_url": course.icon_url
        }
    return render_template('all_courses.html', courses=courses_dict)

@app.route('/course/<course_id>')
def course_details(course_id):
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for('home'))
    return render_template('course.html', course=course)

@app.route('/register/<course_id>', methods=['GET', 'POST'])
def register(course_id):
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        age = request.form['age']
        clas = request.form['class']
        convenient_dates = request.form['convenient_dates']
        email = request.form['email']
        phone = request.form['phone']
        computer = request.form.get('computer', 'personal')
        
        if not all([full_name, email, phone, age, clas]):
            flash('Please fill all fields', 'error')
            return redirect(url_for('register', course_id=course_id))
        
        try:
            new_student = Student(
                full_name=full_name,
                age=int(age),
                class_name=clas,
                convenient_dates=convenient_dates,
                computer=computer,
                email=email,
                phone=phone,
                course_id=course_id,
                course_title=course.title,
                registration_date=datetime.now(timezone.utc),
                status='Pending'
            )
            db.session.add(new_student)
            db.session.commit()
            flash('Գրանցումը հաջողվեց: Մենք շուտով կկապվենք ձեզ հետ', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Email already registered for this course', 'error')
    
    return render_template('register.html', course=course)

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    
    if not all([name, email, message]):
        flash('Please fill all fields', 'error')
        return redirect(url_for('home') + '#contact')
    
    try:
        msg = Message(
            subject=f"New message from {name} - LogicLab Contact Form",
            recipients=[os.getenv('ADMIN_EMAIL')],
            body=f"Name: {name}\nEmail: {email}\nMessage: {message}\n\nSent from LogicLab contact form"
        )
        mail.send(msg)
        flash('Ձեր հաղորդագրությունը հաջողությամբ ուղարկվել է!', 'success')
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        flash('Failed to send your message. Please try again later.', 'error')
    
    return redirect(url_for('home') + '#contact')




# User routes
@app.route('/login', methods=['GET', 'POST'])
def user_login():    
    if request.method == 'POST':
        # api_key = request.form.get('api_key')
        # decoded_key = DATA_MANAGER._decode_api_key(api_key, expiration_months=13)
        # if decoded_key['valid']:
        #     session['user_logged_in'] = True
        #     session['api_key'] = api_key
        #     return redirect(url_for('user_dashboard'))
        flash('Invalid API Key', 'error')
    return render_template('users/login.html')

@app.route('/logout')
def user_logout():
    # session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])

def user_dashboard():
    # course_id="machine_learning"
    # materials = DATA_MANAGER.get_materials()
    # all_materials = list(materials.find({"_id": course_id}))
    # return render_template('users/profile.html', course_id = course_id, materials=all_materials[0])
    return "Dashboard"




# -------------------------
# Admin Routes
# -------------------------

@app.route('/admin')
def admin_dashboard():
    courses = Course.query.all()
    total_students = Student.query.count()
    recent_visitors = Visitor.query.order_by(Visitor.timestamp.desc()).limit(5).all()
    return render_template('admin/dashboard.html',
                        courses=courses,
                        total_students=total_students,
                        recent_visitors=recent_visitors)

@app.route('/admin/logout')
def admin_logout():

    return redirect(url_for('admin_login'))

@app.route('/admin/courses/edit/<course_id>', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    try:
        courses_collection = Course.query.all()
        instructors_collection = Instructor.query.all()
        
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


@app.route('/admin/students')
def admin_students():
    courses_collection = Course.query.all()
    registrations = Student.query.all()
    course_filter = request.args.get('course_id')
    query = {}
    if course_filter:
        query['course_id'] = course_filter
    
    all_students = list(registrations.find(query))
    all_courses = list(courses_collection.find())
    return render_template('admin/students.html', students=all_students, courses=all_courses)

@app.route('/admin/student/<student_id>/delete', methods=['POST'])
def admin_delete_student(student_id):
    registrations = Student.query.all()
    student = registrations.find_one({"_id": ObjectId(student_id)})
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('admin_students'))
    
    registrations.delete_one({"_id": ObjectId(student_id)})
    flash('Student registration deleted successfully', 'success')
    return redirect(url_for('admin_students'))


@app.route('/admin/student/<student_id>/update', methods=['POST'])
def admin_update_student(student_id):
    registrations = Student.query.all()
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

# Admin: Instructors
@app.route('/admin/instructors')
def admin_instructors():
    instructors_collection = Instructor.query.all()
    all_instructors = list(instructors_collection.find())
    return render_template('admin/instructors.html', instructors=all_instructors)

@app.route('/admin/materials')
def admin_materials():
    # try:
    # Get all courses and materials counts
    courses = Course.query.filter_by(is_active=True).all()
    all_courses = list(courses.find({"is_active": True}))
    selected_course_id = "machine_learning" # request.args.get('course', '')
    materials = CourseChapter.query.filter_by(course_id=selected_course_id).all()
    all_materials = list(materials.find({"_id": selected_course_id}))
    
    return render_template('admin/materials.html',
                        all_courses=all_courses,
                        selected_course=all_courses[0],
                        materials=all_materials if all_materials else {'materials': []})
    
    # except Exception as e:
    #     current_app.logger.error(f"Error in admin_materials: {str(e)}")
    #     flash('An error occurred while loading materials', 'error')
    #     return redirect(url_for('admin_dashboard'))

# Admin: Visitors
@app.route('/admin/visitors')
def admin_visitors():
    visits = Visitor.query.order_by(Visitor.timestamp.desc()).limit(100)
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

@app.route('/admin/courses')
def admin_courses():
    courses = Course.query.all()
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/courses/add', methods=['GET', 'POST'])
def admin_add_course():
    if request.method == 'POST':
        try:
            course = Course(
                course_id=request.form['course_id'],
                title=request.form['title'],
                duration=request.form['duration'],
                start_date=request.form['start_date'],
                schedule=request.form['schedule'],
                instructors=request.form.getlist('instructor'),
                capacity=int(request.form['capacity']),
                monthly_payment=int(request.form['monthly_payment']),
                total_payment=int(request.form['total_payment']),
                is_active=('is_active' in request.form),
                portfolio=request.form.get('portfolio'),
                curriculum=request.form.get('curriculum'),
                icon_url=request.form.get('icon_url')
            )
            db.session.add(course)
            db.session.commit()
            flash('Course added successfully', 'success')
            return redirect(url_for('admin_courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding course: {str(e)}', 'error')
    
    instructors = Instructor.query.all()
    return render_template('admin/add_course.html', instructors=instructors)

@app.route('/admin/courses/delete/<course_id>', methods=['POST'])
def admin_delete_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        flash('Course not found', 'error')
    elif course.students.count() > 0:
        flash('Cannot delete course with registered students', 'error')
    else:
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully', 'success')
    return redirect(url_for('admin_courses'))

# -------------------------
# API Routes
# -------------------------

@app.route('/api/courses', methods=['GET'])
def api_courses():
    courses = Course.query.filter_by(is_active=True).all()
    return jsonify([{
        "course_id": c.course_id,
        "title": c.title,
        "duration": c.duration,
        "start_date": c.start_date.isoformat() if c.start_date else None
    } for c in courses])

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    course_id = data.get('course_id')
    course = Course.query.get(course_id)
    if not course or not course.is_active:
        return jsonify({"error": "Invalid course"}), 400
    
    if Student.query.filter_by(email=data['email'], course_id=course_id).first():
        return jsonify({"error": "Email already registered for this course"}), 400
    
    student = Student(
        full_name=data['full_name'],
        email=data['email'],
        phone=data['phone'],
        course_id=course_id,
        course_title=course.title,
        registration_date=datetime.now(timezone.utc),
        status='Pending'
    )
    db.session.add(student)
    db.session.commit()
    return jsonify({"message": "Registration successful"}), 201

# Optional: run directly
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5001, debug=True)