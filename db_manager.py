import os
import hashlib
import socket
from datetime import datetime
import requests
from flask import request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from user_agents import parse
from flask_mail import Message
from models import Course, Registration, Admin, User, Instructor, Visitor, Material
from token_manager import TokenManager  # assuming your TokenManager is in token_manager.py


class DataManager(TokenManager):
    def __init__(self, app, uri):
        super().__init__()
        self.app = app
        self.DB_URI = uri
        self.engine = create_engine(self.DB_URI, echo=False, future=True)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    @staticmethod
    def generate_api_key():
        return hashlib.sha256(os.urandom(32)).hexdigest()

    def get_session(self):
        """Get a SQLAlchemy session"""
        return self.Session()

    # ======== Table Getters ========
    def get_courses(self):
        return self.get_session().query(Course)

    def get_registrations(self):
        return self.get_session().query(Registration)

    def get_admins(self):
        return self.get_session().query(Admin)

    def get_users(self):
        return self.get_session().query(User)

    def get_instructors(self):
        return self.get_session().query(Instructor)

    def get_visits(self):
        return self.get_session().query(Visitor)

    def get_materials(self):
        return self.get_session().query(Material)

    # ======== Materials Management ========
    def get_materials_by_course_id(self, course_id):
        return self.get_session().query(Material).filter_by(course_id=course_id).all()

    def add_material(self, course_id, lesson_key, lesson_data):
        session = self.get_session()
        try:
            material = Material(
                course_id=course_id,
                lesson_key=lesson_key,
                title=lesson_data.get('title', 'Untitled Lesson'),
                presentations=lesson_data.get('presentations', []),
                code=lesson_data.get('code', []),
                other=lesson_data.get('other', [])
            )
            session.add(material)
            session.commit()
            return ('Lesson added successfully', 'success')
        except Exception as e:
            session.rollback()
            return (f'Error adding material: {str(e)}', 'error')

    def update_material(self, material_id, updated_data):
        session = self.get_session()
        try:
            material = session.query(Material).get(material_id)
            if not material:
                return False
            for key, value in updated_data.items():
                setattr(material, key, value)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False

    def delete_lesson(self, material_id):
        session = self.get_session()
        try:
            material = session.query(Material).get(material_id)
            if material:
                session.delete(material)
                session.commit()
                return True
            return False
        except Exception as e:
            self.app.logger.error(f"Error deleting lesson: {str(e)}")
            session.rollback()
            return False

    # ======== Visits Management ========
    def track_visit(self):
        session = self.get_session()
        ip_address = request.remote_addr
        user_agent_str = request.headers.get('User-Agent', '')
        user_agent = parse(user_agent_str)
        referrer = request.headers.get('Referer', '')
        path = request.path

        try:
            hostname = socket.gethostbyaddr(ip_address)[0]
        except (socket.herror, socket.gaierror):
            hostname = None

        visit = Visitor(
            ip_address=ip_address,
            hostname=hostname,
            user_agent_raw=user_agent_str,
            browser=user_agent.browser.family,
            browser_version=user_agent.browser.version_string,
            os=user_agent.os.family,
            os_version=user_agent.os.version_string,
            device=user_agent.device.family,
            is_mobile=user_agent.is_mobile,
            is_tablet=user_agent.is_tablet,
            is_pc=user_agent.is_pc,
            is_bot=user_agent.is_bot,
            referrer=referrer,
            path=path,
            timestamp=datetime.now(),
            date=datetime.now().strftime('%Y-%m-%d'),
            time=datetime.now().strftime('%H:%M:%S')
        )

        try:
            session.add(visit)
            session.commit()
        except Exception as e:
            self.app.logger.error(f"Failed to track visit: {str(e)}")
            session.rollback()

    def get_ip_geolocation(self, ip_address):
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip_address}?fields=status,message,continent,continentCode,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,offset,currency,isp,org,as,asname,reverse,mobile,proxy,hosting,query'
            )
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
            return None
        except Exception as e:
            self.app.logger.error(f"Geolocation error: {e}")
            return None

    # ======== Email ========
    def send_status_email(self, mail, to_email, student_name, course_name, new_status):
        try:
            subject = f"Your registration status for {course_name} has been updated"

            status_messages = {
                'pending': "Your registration is currently being reviewed by our team. We will notify you once a decision has been made. Thank you for your patience.",
                'confirmed': "Great news! Your registration has been confirmed and you are now officially enrolled in the course. You will receive further details about course materials and schedule shortly.",
                'rejected': "We regret to inform you that your registration could not be accepted at this time. This may be due to capacity limits or prerequisite requirements. Please feel free to contact us for more information about future opportunities.",
                'completed': "Congratulations on successfully completing the course! We hope you found the experience valuable and wish you continued success in your learning journey.",
                'cancelled': "Your registration has been cancelled as requested. If this was done in error or if you wish to re-enroll, please contact our support team.",
                'waitlisted': "You have been placed on the waitlist for this course. We will notify you immediately if a spot becomes available.",
                'expired': "Your registration has expired due to non-payment or lack of confirmation within the required timeframe. Please contact us if you wish to discuss re-enrollment options."
            }

            # Plain text version
            body = f"""
            Dear {student_name},

            Your registration status for {course_name} has been updated to: {new_status.capitalize()}.

            {status_messages.get(new_status, 'Your registration status has been updated. Please contact us for more details.')}

            If you have any questions or concerns, please don't hesitate to contact our support team at support@logiclab.am or call us during business hours.

            Best regards,
            Logic Lab Team
            """

            # HTML version
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: auto; padding: 20px; background-color: #f4f4f4; border-radius: 10px; border: 1px solid #e0e0e0;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #222; margin-bottom: 10px;">Logic Lab</h1>
                        <hr style="border: 1px solid #FFD700; width: 50%;">
                    </div>
                    
                    <h2 style="color: #222;">Հարգելի {student_name},</h2>
                    
                    <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FFD700;">
                        <p style="margin-bottom: 15px;">
                            Ձեր գրանցման կարգավիճակը <strong>{course_name}</strong> դասընթացի համար թարմացվել է՝ 
                            <span style="color: #FFC000; font-weight: bold; font-size: 1.1em;">{new_status.capitalize()}</span>
                        </p>
                        
                        <div style="background-color: #c0e4ea; padding: 15px; border-radius: 5px; margin: 15px 0;">
                            <p style="margin: 0; font-style: italic; color: #222;">
                                {status_messages.get(new_status, 'Your registration status has been updated. Please contact us for more details.')}
                            </p>
                        </div>
                    </div>
                    
                    <div style="background-color: #c0e4ea; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 0;">
                            <strong>Օգնության կարիք ունե՞ք:</strong> Եթե ունեք որևէ հարց կամ մտահոգություն, 
                            խնդրում ենք կապ հաստատել մեր աջակցության թիմի հետ՝ 
                            <a href="mailto:info.logic.laboratory@gmail.com" style="color: #FFC000;">info.logic.laboratory@gmail.com</a> 
                            կամ զանգահարեք նշված հեռախոսահամարով:
                        </p>
                    </div>
                    
                    <br>
                    <p style="margin-bottom: 5px;">Հարգանքով,</p>
                    <p style="margin: 0;"><strong style="color: #222;">Logic Lab թիմ</strong></p>
                </div>

                <footer style="font-size: 13px; color: #666; margin-top: 40px;">
                    <img src="https://res.cloudinary.com/dujmbcltl/image/upload/v1750706217/Untitled-1_hitauw.png" alt="LogicLab Logo" width="120" style="display: block; margin-bottom: 10px;"></img>
                    <a href="https://maps.app.goo.gl/vgGPH78t6scVKVxT8" target="_blank">📍 Վանաձոր, Տիգրան Մեծ պողոտա 18</a><br>
                    🌐 <a href="https://www.logiclab.am" target="_blank">www.logiclab.am</a><br>
                    📧 info.logic.laboratory@gmail.com<br>
                    📞 094 75 26 62
                </footer>
            </body>
            </html>
            """

            msg = Message(
                subject=subject,
                recipients=[to_email],
                body=body
            )
            msg.html = html

            mail.send(msg)
            return True

        except Exception as e:
            print(f"Failed to send status email: {str(e)}")
            self.app.logger.error(f"Failed to send status email: {str(e)}")
            return False

