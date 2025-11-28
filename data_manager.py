import os
import socket
import hashlib
import requests
from functools import wraps
from user_agents import parse
from datetime import datetime
from pymongo import MongoClient
from urllib.parse import quote_plus
from flask_mail import Mail, Message
from flask import request, redirect, url_for, flash,  session
import uuid
from datetime import datetime, timedelta

from models import TokenManager


class DataManager(TokenManager):
    def __init__(self, app, uri):
        super().__init__()
        self.app = app
        self.MONGO_URI = uri

    @staticmethod
    def generate_api_key():
        return hashlib.sha256(os.urandom(32)).hexdigest()

    def get_db(self):
        """Get MongoDB database connection"""
        client = MongoClient(self.MONGO_URI)
        db = client.education_platform
        return db

    def get_collections(self):
        """Get all required collections"""
        db = self.get_db()
        return (
            db.courses,
            db.registrations,
            db.admins,
            db.users,
            db.instructors,
            db.visits,
            db.materials
        )

    # Existing collection getters remain the same
    def get_courses(self):
        db = self.get_db()
        return db.courses

    def get_registrations(self):
        db = self.get_db()
        return db.registrations

    def get_admins(self):
        db = self.get_db()
        return db.admins

    def get_users(self):
        db = self.get_db()
        return db.users

    def get_instructors(self):
        db = self.get_db()
        return db.instructors

    def get_visits(self):
        db = self.get_db()
        return db.visits

    # ========== Materials Management Methods ==========
    def get_materials(self):
        """Get all materials for a specific course"""
        db = self.get_db()
        return db.materials

    def get_ml_projects(self):
        """Get all ML projects"""
        db = self.get_db()
        return db.ml_projects

    def get_materials_by_course_id(self, course_id):
        all_materials = self.get_materials()
        materials = all_materials.find({"_id": course_id})
        return list(materials)

    def add_material(self, course_id, lesson_key, lesson_data):
        """
        Add a new lesson to course materials or update existing lesson
        
        Args:
            course_id: ID of the course
            lesson_key: Key for the lesson (e.g., "lesson_1")
            lesson_data: Dictionary containing lesson data with structure:
                {
                    "tittle": "Lesson Title",
                    "presentations": [url1, url2],
                    "code": [url1],
                    "other": []
                }
        Returns:
            Tuple: (success, message)
        """
        materials_collection = self.get_materials()
        
        try:
            # Validate inputs
            if not course_id or not lesson_key:
                return (False, 'Course ID and lesson key are required')
            
            if not lesson_data or not isinstance(lesson_data, dict):
                return (False, 'Lesson data must be a valid dictionary')
            
            # Check if course material exists
            course_material = materials_collection.find_one({'_id': course_id})
            
            if not course_material:
                # Create new course material with this lesson
                new_course_material = {
                    '_id': course_id,
                    'name': lesson_data.get('name', 'Unnamed Course'),
                    'materials': {
                        lesson_key: lesson_data
                    }
                }
                materials_collection.insert_one(new_course_material)
                return (True, 'New course materials created with lesson added successfully')
            
            # If course exists but has no materials structure yet
            if 'materials' not in course_material:
                course_material['materials'] = {}
            
            # Check if lesson key already exists
            if lesson_key in course_material.get('materials', {}):
                # Update existing lesson
                update_data = {
                    f"materials.{lesson_key}": lesson_data
                }
                result = materials_collection.update_one(
                    {"_id": course_id},
                    {"$set": update_data}
                )
                if result.modified_count > 0:
                    return (True, 'Lesson updated successfully')
                else:
                    return (True, 'No changes were made to the lesson')
            else:
                # Add new lesson without affecting existing ones
                result = materials_collection.update_one(
                    {"_id": course_id},
                    {"$set": {f"materials.{lesson_key}": lesson_data}}
                )
                
                if result.modified_count > 0 or result.upserted_id:
                    return (True, 'Lesson added successfully')
                else:
                    return (True, 'No changes were made to the materials')
                
        except Exception as e:
            self.app.logger.error(f"Error adding material: {str(e)}")
            return (False, f'Error adding material: {str(e)}')

    def add_simple_material(self, course_id, material_data):
        """
        Add a simple material (not a lesson) to course materials
        
        Args:
            course_id: ID of the course
            material_data: Dictionary containing material data
        Returns:
            Tuple: (success, message)
        """
        materials_collection = self.get_materials()
        
        try:
            # Validate inputs
            if not course_id:
                return (False, 'Course ID is required')
            
            if not material_data or not isinstance(material_data, dict):
                return (False, 'Material data must be a valid dictionary')
            
            # Check if course material exists
            course_material = materials_collection.find_one({'_id': course_id})
            
            if not course_material:
                # Create new course material
                new_course_material = {
                    '_id': course_id,
                    'name': material_data.get('name', 'Unnamed Course'),
                    'simple_materials': [material_data]
                }
                materials_collection.insert_one(new_course_material)
                return (True, 'New course materials created with material added successfully')
            
            # Add to existing simple_materials array
            result = materials_collection.update_one(
                {"_id": course_id},
                {"$push": {"simple_materials": material_data}}
            )
            
            if result.modified_count > 0:
                return (True, 'Material added successfully')
            else:
                return (True, 'No changes were made to the materials')
                
        except Exception as e:
            self.app.logger.error(f"Error adding simple material: {str(e)}")
            return (False, f'Error adding material: {str(e)}')

    def update_material(self, course_id, lesson_key, updated_data):
        """
        Update an existing lesson material
        Args:
            course_id: ID of the course
            lesson_key: Key of the lesson to update
            updated_data: Dictionary with updated fields
        """
        materials = self.get_materials()
        
        try:
            update_fields = {}
            
            for key, value in updated_data.items():
                update_fields[f"materials.{lesson_key}.{key}"] = value
            
            result = materials.update_one(
                {"_id": course_id},
                {"$set": update_fields}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            self.app.logger.error(f"Error updating material: {str(e)}")
            return False

    def delete_lesson(self, course_id, lesson_key):
        """
        Delete a lesson from course materials
        
        Args:
            course_id: ID of the course
            lesson_key: Key of the lesson to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        materials_collection = self.get_materials()
        
        try:
            result = materials_collection.update_one(
                {"_id": course_id},
                {"$unset": {f"materials.{lesson_key}": ""}}
            )
            
            # Clean up empty materials object if this was the last lesson
            course_material = materials_collection.find_one({'_id': course_id})
            if course_material and 'materials' in course_material and not course_material['materials']:
                materials_collection.update_one(
                    {"_id": course_id},
                    {"$unset": {"materials": ""}}
                )
                
            return result.modified_count > 0
            
        except Exception as e:
            self.app.logger.error(f"Error deleting lesson: {str(e)}")
            return False

    # ========== ML Projects Management Methods ==========
    
    def add_ml_project(self, project_data):
        """
        Add a new ML project
        
        Args:
            project_data: Dictionary containing project data with structure:
                {
                    "title": "Project Title",
                    "student_name": "Student Name",
                    "student_email": "email@example.com",
                    "student_phone": "+374 XX XXX XXX",
                    "course_id": "machine_learning",
                    "description": "Project description",
                    "github_url": "https://github.com/...",
                    "demo_url": "https://...",
                    "colab_notebook_url": "https://colab.research.google.com/...",
                    "files": {
                        "data": ["url1"],
                        "materials": ["url1", "url2"],
                        "models": ["url1"],
                        "main_py": "url",
                        "names_py": "url",
                        "processor_py": "url",
                        "requirements_txt": "url",
                        "utils_py": "url"
                    },
                    "visualizations": [
                        {
                            "title": "Confusion Matrix",
                            "image_url": "url",
                            "description": "Model performance visualization"
                        }
                    ],
                    "metrics": {
                        "accuracy": 0.95,
                        "precision": 0.93,
                        "recall": 0.92,
                        "f1_score": 0.92,
                        "custom_metrics": {}
                    },
                    "technologies": ["Python", "Scikit-learn", "Pandas"],
                    "created_at": datetime
                }
        Returns:
            Tuple: (success, message, project_id)
        """
        ml_projects = self.get_ml_projects()
        
        try:
            if not project_data or not isinstance(project_data, dict):
                return (False, 'Project data must be a valid dictionary', None)
            
            # Validate required fields
            required_fields = ['title', 'student_name', 'course_id']
            for field in required_fields:
                if field not in project_data or not project_data[field]:
                    return (False, f'{field} is required', None)
            
            # Set created_at if not provided
            if 'created_at' not in project_data:
                project_data['created_at'] = datetime.now()
            
            # Set is_featured default to False
            if 'is_featured' not in project_data:
                project_data['is_featured'] = False
            
            # Insert the project
            result = ml_projects.insert_one(project_data)
            
            return (True, 'Project added successfully', str(result.inserted_id))
            
        except Exception as e:
            self.app.logger.error(f"Error adding ML project: {str(e)}")
            return (False, f'Error adding project: {str(e)}', None)
    
    def update_ml_project(self, project_id, updated_data):
        """
        Update an existing ML project
        
        Args:
            project_id: ID of the project to update
            updated_data: Dictionary with updated fields
        Returns:
            Tuple: (success, message)
        """
        ml_projects = self.get_ml_projects()
        
        try:
            from bson import ObjectId
            
            # Update modified_at timestamp
            updated_data['modified_at'] = datetime.now()
            
            result = ml_projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": updated_data}
            )
            
            if result.modified_count > 0:
                return (True, 'Project updated successfully')
            else:
                return (True, 'No changes were made')
                
        except Exception as e:
            self.app.logger.error(f"Error updating ML project: {str(e)}")
            return (False, f'Error updating project: {str(e)}')
    
    def delete_ml_project(self, project_id):
        """
        Delete an ML project
        
        Args:
            project_id: ID of the project to delete
        Returns:
            Tuple: (success, message)
        """
        ml_projects = self.get_ml_projects()
        
        try:
            from bson import ObjectId
            
            result = ml_projects.delete_one({"_id": ObjectId(project_id)})
            
            if result.deleted_count > 0:
                return (True, 'Project deleted successfully')
            else:
                return (False, 'Project not found')
                
        except Exception as e:
            self.app.logger.error(f"Error deleting ML project: {str(e)}")
            return (False, f'Error deleting project: {str(e)}')
    
    def get_ml_project_by_id(self, project_id):
        """Get a specific ML project by ID"""
        ml_projects = self.get_ml_projects()
        try:
            from bson import ObjectId
            return ml_projects.find_one({"_id": ObjectId(project_id)})
        except Exception as e:
            self.app.logger.error(f"Error getting ML project: {str(e)}")
            return None

    # ========== Visits Management Methods ==========

    def track_visit(self, visits):
        ip_address = request.remote_addr
        user_agent_str = request.headers.get('User-Agent', '')
        user_agent = parse(user_agent_str)
        referrer = request.headers.get('Referer', '')
        path = request.path
        
        try:
            hostname = socket.gethostbyaddr(ip_address)[0]
        except (socket.herror, socket.gaierror):
            hostname = None
        
        visit_data = {
            'ip_address': ip_address,
            'hostname': hostname,
            'user_agent_raw': user_agent_str,
            'browser': user_agent.browser.family,
            'browser_version': user_agent.browser.version_string,
            'os': user_agent.os.family,
            'os_version': user_agent.os.version_string,
            'device': user_agent.device.family,
            'is_mobile': user_agent.is_mobile,
            'is_tablet': user_agent.is_tablet,
            'is_pc': user_agent.is_pc,
            'is_bot': user_agent.is_bot,
            'referrer': referrer,
            'path': path,
            'timestamp': datetime.now(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S')
        }
        
        try:
            visits.insert_one(visit_data)
        except Exception as e:
            self.app.logger.error(f"Failed to track visit: {str(e)}")

    def get_ip_geolocation(self, ip_address):
        try:
            response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=status,message,continent,continentCode,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,offset,currency,isp,org,as,asname,reverse,mobile,proxy,hosting,query')
            data = response.json()
            
            if data.get('status') == 'success':
                return {
                    'country': data.get('country', 'Unknown'),
                    'country_code': data.get('countryCode', ''),
                    'region': data.get('regionName', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'zip': data.get('zip', ''),
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                    'timezone': data.get('timezone', ''),
                    'isp': data.get('isp', ''),
                    'is_mobile': data.get('mobile', False),
                    'is_proxy': data.get('proxy', False),
                    'is_hosting': data.get('hosting', False)
                }
            
            try:
                with geoip2.database.Reader('GeoLite2-City.mmdb') as reader:
                    response = reader.city(ip_address)
                    return {
                        'country': response.country.name,
                        'country_code': response.country.iso_code,
                        'region': response.subdivisions.most_specific.name if response.subdivisions else None,
                        'city': response.city.name,
                        'postal_code': response.postal.code,
                        'latitude': response.location.latitude,
                        'longitude': response.location.longitude,
                        'timezone': response.location.time_zone,
                        'is_in_european_union': response.country.is_in_european_union,
                        'accuracy_radius': response.location.accuracy_radius
                    }
            except:
                return None
                
        except Exception as e:
            self.app.logger.error(f"Geolocation error: {e}")
            return None

    def send_status_email(self, mail, to_email, student_name, course_name, new_status):
        try:
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
            LogicLab Team
            """
            
            msg = Message(
                subject=subject,
                recipients=[to_email],
                body=body
            )
            mail.send(msg)
            return True
        except Exception as e:
            self.app.logger.error(f"Failed to send status email: {str(e)}")
            return False

# Admin authentication decorator
def admin_required(f):
    def wrapper(*args, **kwargs):
        if 'admin_logged_in' not in session:
            provided_key = request.args.get('api_key') or request.form.get('api_key')
            if not provided_key:
                return redirect(url_for('admin_login'))
            
            admins = DataManager.get_admins()
            admin = admins.find_one({"api_key": provided_key})
            if not admin:
                flash('Invalid API key', 'error')
                return redirect(url_for('admin_login'))
            
            session['admin_logged_in'] = True
            session['api_key'] = provided_key
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


# User authentication decorator
def user_required(f):
    def wrapper(*args, **kwargs):
        if 'user_logged_in' not in session:
            provided_key = request.args.get('api_key') or request.form.get('api_key')
            if not provided_key:
                return redirect(url_for('user_login'))
            
            decoded_key = DataManager._decode_api_key(provided_key, expiration_months=13)
            if not decoded_key['valid']:
                flash('Invalid API key', 'error')
                return redirect(url_for('login'))
            
            session['user_logged_in'] = True
            session['api_key'] = provided_key
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

DATA_MANAGER_INSTANCE = None

def set_global_data_manager(instance):
    global DATA_MANAGER_INSTANCE
    DATA_MANAGER_INSTANCE = instance

def get_global_data_manager():
    return DATA_MANAGER_INSTANCE
