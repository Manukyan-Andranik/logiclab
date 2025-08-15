from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from extensions import DATA_MANAGER, admin_required, user_required
from utils import is_valid_url, generate_download_url

material_bp = Blueprint('material', __name__)

@material_bp.route('/admin/materials')
@admin_required
def admin_materials():
    courses = DATA_MANAGER.get_courses()
    all_courses = list(courses.find({"is_active": True}))
    selected_course_id = "machine_learning"
    materials = DATA_MANAGER.get_materials()
    all_materials = list(materials.find({"_id": selected_course_id}))
    
    return render_template('admin/materials.html',
                        all_courses=all_courses,
                        selected_course=all_courses[0],
                        materials=all_materials if all_materials else {'materials': []})


@material_bp.route('/dashboard')
@user_required
def user_dashboard():
    course_id="machine_learning"
    materials = DATA_MANAGER.get_materials()
    all_materials = list(materials.find({"_id": course_id}))
    return render_template('users/profile.html', course_id = course_id, materials=all_materials[0])
