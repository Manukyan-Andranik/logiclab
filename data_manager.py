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
            Tuple: (message, message_type)
        """
        materials_collection = self.get_materials()
        
        try:
            # Check if course material exists
            course_material = materials_collection.find_one({'_id': course_id})
            
            if not course_material:
                # Create new course material with this lesson
                new_course_material = {
                    '_id': course_id,
                    'name': lesson_data.get('course_name', 'Unnamed Course'),
                    'materials': {
                        lesson_key: lesson_data
                    }
                }
                materials_collection.insert_one(new_course_material)
                return ('New course materials created with lesson added successfully', 'success')
            
            # If course exists but has no materials structure yet
            if 'materials' not in course_material:
                course_material['materials'] = {}
            
            # Add or update the lesson
            update_data = {
                f"materials.{lesson_key}": lesson_data
            }
            
            # If we want to preserve existing name when adding lessons
            if 'name' in course_material and 'name' in lesson_data:
                del lesson_data['name']
            
            result = materials_collection.update_one(
                {"_id": course_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return ('Lesson added/updated successfully', 'success')
            else:
                return ('No changes were made to the materials', 'info')
                
        except Exception as e:
            return (f'Error adding material: {str(e)}', 'error')

    def update_material(self, course_id, material_index, updated_data):
        """
        Update an existing material
        Args:
            course_id: ID of the course
            material_index: Index of the material in the materials array
            updated_data: Dictionary with updated fields
        """
        materials = self.get_materials()
        update_fields = {}
        
        for key, value in updated_data.items():
            update_fields[f"materials.{material_index}.{key}"] = value
        
        result = materials.update_one(
            {"_id": course_id},
            {"$set": update_fields}
        )
        return result.modified_count > 0

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
