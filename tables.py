from datetime import datetime, timezone
from sqlalchemy import CheckConstraint

from extensions import db

# =========================
# Courses Table
# =========================
class Course(db.Model):
    __tablename__ = "courses"

    course_id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    duration = db.Column(db.Text)
    start_date = db.Column(db.Date)
    schedule = db.Column(db.Text)
    instructors = db.Column(db.ARRAY(db.Text))  # list of instructor names
    capacity = db.Column(db.Integer)
    monthly_payment = db.Column(db.Integer)
    total_payment = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True, index=True)
    portfolio = db.Column(db.Text)
    curriculum = db.Column(db.Text)
    icon_url = db.Column(db.Text)

    # Relationships
    chapters = db.relationship(
        "CourseChapter",
        backref="course",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    students = db.relationship(
        "Student",
        backref="course",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )


class CourseChapter(db.Model):
    __tablename__ = "course_chapters"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(
        db.String(256),
        db.ForeignKey("courses.course_id", ondelete="CASCADE")
    )
    title = db.Column(db.Text)
    content = db.Column(db.ARRAY(db.Text))  # list of bullet points


# =========================
# Students Table
# =========================
class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.Text, nullable=False)
    age = db.Column(db.Integer)
    class_name = db.Column("class", db.Text)  # `class` reserved in Python
    convenient_dates = db.Column(db.Text)
    computer = db.Column(db.Text, CheckConstraint("computer IN ('personal', 'logiclab')"))
    email = db.Column(db.Text, unique=True)
    phone = db.Column(db.Text)
    course_id = db.Column(
        db.String(64),
        db.ForeignKey("courses.course_id", ondelete="SET NULL")
    )
    course_title = db.Column(db.Text)
    registration_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.Text, CheckConstraint(
        "status IN ('0', 'Pending', 'Confirmed', 'Rejected', 'Completed')"
    ))


# =========================
# Instructors Table
# =========================
class Instructor(db.Model):
    __tablename__ = "instructors"

    instructor_id = db.Column(db.String(64), primary_key=True)
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    institution = db.Column(db.Text)
    degree = db.Column(db.Text)
    field_of_study = db.Column(db.Text)
    profession = db.Column(db.Text)
    specialization = db.Column(db.Text)
    work_experience = db.Column(db.Integer)
    skills = db.Column(db.ARRAY(db.Text))
    software_proficiency = db.Column(db.ARRAY(db.Text))
    phone = db.Column(db.Text)
    linkedin = db.Column(db.Text)
    web = db.Column(db.Text)
    photo_url = db.Column(db.Text)

    companies = db.relationship(
        "InstructorCompany",
        backref="instructor",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )


class InstructorCompany(db.Model):
    __tablename__ = "instructor_companies"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    instructor_id = db.Column(
        db.String(64),
        db.ForeignKey("instructors.instructor_id", ondelete="CASCADE")
    )
    company = db.Column(db.Text)
    type = db.Column(db.Text)
    role = db.Column(db.Text)


# =========================
# Visitors Table
# =========================
class Visitor(db.Model):
    __tablename__ = "visitors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip_address = db.Column(db.String(45), index=True)  # supports IPv4 & IPv6
    hostname = db.Column(db.Text)
    user_agent_raw = db.Column(db.Text)
    browser = db.Column(db.Text)
    browser_version = db.Column(db.String(50))
    os = db.Column(db.Text)
    os_version = db.Column(db.String(50))
    device = db.Column(db.Text)
    is_mobile = db.Column(db.Boolean, default=False, index=True)
    is_tablet = db.Column(db.Boolean, default=False)
    is_pc = db.Column(db.Boolean, default=False)
    is_bot = db.Column(db.Boolean, default=False)
    referrer = db.Column(db.Text)
    path = db.Column(db.Text)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    date = db.Column(db.Date)
    time = db.Column(db.String(20))
