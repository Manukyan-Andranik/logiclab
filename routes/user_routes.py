from flask import render_template, request, redirect, url_for, flash, session
from . import user_routes
from data_manager import DATA_MANAGER, user_required

@user_routes.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        if DATA_MANAGER._decode_api_key(api_key, 13)['valid']:
            session['user_logged_in'] = True
            session['api_key'] = api_key
            return redirect(url_for('user.user_dashboard'))
        flash('Invalid API Key', 'error')
    return render_template('users/login.html')

@user_routes.route('/logout')
def user_logout():
    session.clear()
    return redirect(url_for('site.home'))

@user_routes.route('/dashboard', methods=['GET', 'POST'])
@user_required
def user_dashboard():
    course_id = "machine_learning"
    materials = list(DATA_MANAGER.get_materials().find({"_id": course_id}))
    return render_template('users/profile.html', course_id=course_id, materials=materials[0])
