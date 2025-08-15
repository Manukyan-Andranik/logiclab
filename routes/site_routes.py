from flask import render_template, request, redirect, url_for, flash
from . import site_routes
from datetime import datetime
from flask_mail import Message
from utils import get_ids, find_by_id
from . import DATA_MANAGER, mail

@site_routes.route('/')
def home():
    courses = list(DATA_MANAGER.get_courses().find({"is_active": True}))
    instructors = list(DATA_MANAGER.get_instructors().find())
    DATA_MANAGER.track_visit(DATA_MANAGER.get_visits())

    all_courses = {id: find_by_id(courses, id) for id in get_ids(courses)}
    all_instructors = {id: find_by_id(instructors, id) for id in get_ids(instructors)}

    return render_template('../index.html', courses=all_courses, instructors=all_instructors)

@site_routes.route('/instructors')
def instructors():
    instructors = list(DATA_MANAGER.get_instructors().find())
    DATA_MANAGER.track_visit(DATA_MANAGER.get_visits())
    all_instructors = {id: find_by_id(instructors, id) for id in get_ids(instructors)}
    return render_template("instructors.html", instructors=all_instructors)

@site_routes.route('/all_courses')
def all_courses():
    courses = list(DATA_MANAGER.get_courses().find({"is_active": True}))
    instructors = list(DATA_MANAGER.get_instructors().find())
    DATA_MANAGER.track_visit(DATA_MANAGER.get_visits())
    all_courses = {id: find_by_id(courses, id) for id in get_ids(courses)}
    return render_template('all_courses.html', courses=all_courses)

@site_routes.route('/course/<course_id>')
def course_details(course_id):
    course = DATA_MANAGER.get_courses().find_one({"_id": course_id})
    if not course:
        return redirect(url_for('site.home'))
    return render_template('course.html', course=course, course_id=course_id)

@site_routes.route('/register/<course_id>', methods=['GET', 'POST'])
def register(course_id):
    course = DATA_MANAGER.get_courses().find_one({"_id": course_id})
    if not course:
        return redirect(url_for('site.home'))

    if request.method == 'POST':
        form = request.form
        if not all([form['full_name'], form['email'], form['phone'], form['age'], form['class']]):
            flash('Please fill all fields', 'error')
            return redirect(url_for('site.register', course_id=course_id))

        DATA_MANAGER.get_registrations().insert_one({
            'full_name': form['full_name'],
            'age': form['age'],
            'class': form['class'],
            'convenient_dates': form['convenient_dates'],
            'computer': form.get('computer', 'no'),
            'email': form['email'],
            'phone': form['phone'],
            'course_id': course_id,
            'course_title': course['title'],
            'registration_date': datetime.now(),
            'status': 'pending'
        })
        flash('Գրանցումը հաջողվեց: Մենք շուտով կկապվենք ձեզ հետ', 'success')
    return render_template('register.html', course=course, course_id=course_id)

@site_routes.route('/contact', methods=['POST'])
def contact():
    form = request.form
    if not all([form['name'], form['email'], form['message']]):
        flash('Please fill all fields', 'error')
        return redirect(url_for('site.home') + '#contact')
    
    try:
        msg = Message(
            subject=f"New message from {form['name']} - LogicLab Contact Form",
            recipients=[os.getenv('ADMIN_EMAIL')],
            body=f"Name: {form['name']}\nEmail: {form['email']}\nMessage: {form['message']}"
        )
        mail.send(msg)
        flash('Ձեր հաղորդագրությունը հաջողությամբ ուղարկվել է!', 'success')
    except Exception as e:
        flash(f'Error sending message: {str(e)}', 'error')
    return redirect(url_for('site.home') + '#contact')
