from flask import render_template, request, redirect, url_for, flash, session
from . import admin_routes
from data_manager import DATA_MANAGER, admin_required

@admin_routes.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        if DATA_MANAGER.get_admins().find_one({"api_key": api_key}):
            session['admin_logged_in'] = True
            session['api_key'] = api_key
            return redirect(url_for('admin.admin_dashboard'))
        flash('Invalid API Key', 'error')
    return render_template('admin/login.html')

@admin_routes.route('/admin')
@admin_required
def admin_dashboard():
    courses = list(DATA_MANAGER.get_courses().find())
    registrations = DATA_MANAGER.get_registrations()
    total_students = registrations.count_documents({})
    visits = list(DATA_MANAGER.get_visits().find().sort('timestamp', -1).limit(5))

    for c in courses:
        c_id = c['_id']
        for status in ['pending', 'confirmed', 'rejected', 'completed']:
            c[f"{status}_count"] = registrations.count_documents({'course_id': c_id, 'status': status})

    return render_template('admin/dashboard.html', courses=courses, total_students=total_students, recent_visitors=visits)

@admin_routes.route('/admin/courses/delete/<course_id>', methods=['POST'])
@admin_required
def admin_delete_course(course_id):
    registrations = DATA_MANAGER.get_registrations()
    if registrations.count_documents({"course_id": course_id}) > 0:
        flash('Cannot delete course with registered students', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    result = DATA_MANAGER.get_courses().delete_one({"_id": course_id})
    flash('Course deleted successfully' if result.deleted_count == 1 else 'Course not found', 'success' if result.deleted_count == 1 else 'error')
    return redirect(url_for('admin.admin_dashboard'))
