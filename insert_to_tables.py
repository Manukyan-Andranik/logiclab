import json
from datetime import datetime
from datetime import timezone
from app import create_app
from extensions import db
from tables import Course, CourseChapter, Instructor, InstructorCompany, Student, Visitor

app = create_app()


with app.app_context():  # <--- critical: enable app context

    # courses
    # Load JSON data
    # with open("mongo_exports/courses.json", "r", encoding="utf-8") as f:
    #     courses_data = json.load(f)

    # for course in courses_data:
    #     start_date = datetime.strptime(course.get("start_date"), "%Y-%m-%d").date() if course.get("start_date") else None

    #     new_course = Course(
    #         course_id=course["_id"],
    #         title=course.get("title"),
    #         duration=course.get("duration"),
    #         start_date=start_date,
    #         schedule=course.get("schedule"),
    #         instructors=course.get("instructor", []),
    #         capacity=course.get("capacity"),
    #         monthly_payment=course.get("monthly_payment"),
    #         total_payment=course.get("total_payment"),
    #         is_active=course.get("is_active", True),
    #         portfolio=course.get("portfolio"),
    #         curriculum=course.get("curriculum"),
    #         icon_url=course.get("icon_url")
    #     )

    #     # Add chapters
    #     for chapter in course.get("chapters", []):
    #         separator = "|mysep|"
    #         content=separator.join(chapter.get("content", [])).split(separator)
    #         print(type(content))
    #         print(content)
    #         new_chapter = CourseChapter(
    #             title=chapter.get("title"),
    #             content=content,
    #             course=new_course
    #         )
    #         db.session.add(new_chapter)
    #         print("_____________")
            
    #     db.session.add(new_course)

    # db.session.commit()
    # print("All courses inserted successfully!")


    # #instructors
    # JSON_FILE = "mongo_exports/instructors.json"
    # with open(JSON_FILE, "r", encoding="utf-8") as f:
    #     instructors_data = json.load(f)

    # # =========================
    # # Insert Data
    # # =========================
    # for instr in instructors_data:
    #     instructor_id = instr["_id"]
    #     education = instr.get("education", {})

    #     # Handle missing fields
    #     first_name = instr.get("firstName")
    #     last_name = instr.get("lastName")
    #     institution = education.get("institution")
    #     degree = education.get("degree")
    #     field_of_study = education.get("fieldOfStudy")
    #     profession = instr.get("profession")
    #     specialization = instr.get("specialization")
    #     work_experience = instr.get("workExperience")
    #     skills = instr.get("skills") or []
    #     software_proficiency = instr.get("softwareProficiency") or []
    #     # Flatten software proficiency if it’s a single string
    #     if len(software_proficiency) == 1 and '\n' in software_proficiency[0]:
    #         software_proficiency = software_proficiency[0].splitlines()
    #     contacts = instr.get("contacts", {})
    #     phone = contacts.get("phone")
    #     linkedin = contacts.get("linkedin")
    #     web = contacts.get("web")
    #     photo_url = instr.get("photo_url")

    #     # Create Instructor
    #     instructor = Instructor(
    #         instructor_id=instructor_id,
    #         first_name=first_name,
    #         last_name=last_name,
    #         institution=institution,
    #         degree=degree,
    #         field_of_study=field_of_study,
    #         profession=profession,
    #         specialization=specialization,
    #         work_experience=work_experience,
    #         skills=skills,
    #         software_proficiency=software_proficiency,
    #         phone=phone,
    #         linkedin=linkedin,
    #         web=web,
    #         photo_url=photo_url
    #     )
    #     db.session.add(instructor)

    #     # Add companies
    #     for comp in instr.get("companies", []):
    #         company = InstructorCompany(
    #             instructor_id=instructor_id,
    #             company=comp.get("company"),
    #             type=comp.get("type"),
    #             role=comp.get("role")
    #         )
    #         db.session.add(company)

    # # =========================
    # # Commit db.session
    # # =========================
    # db.session.commit()
    # print("All instructor data inserted successfully!")



    # students
    # with open("mongo_exports/registrations.json", "r", encoding="utf-8") as f:
    #     students_json = json.load(f)

    # for student_data in students_json:
    #     # Convert age to integer
    #     age = int(student_data.get("age", 0)) if student_data.get("age") else None

    #     # Parse registration date
    #     reg_date_str = student_data.get("registration_date")
    #     registration_date = datetime.fromisoformat(reg_date_str) if reg_date_str else None

    #     # Map JSON status to match table constraint
    #     status_map = {
    #         "confirmed": "Confirmed",
    #         "pending": "Pending",
    #         "rejected": "Rejected",
    #         "completed": "Completed",
    #         "0": "0"
    #     }
    #     status = status_map.get(student_data.get("status", "Pending"), "Pending")

    #     student = Student(
    #         full_name=student_data.get("full_name"),
    #         age=age,
    #         class_name=student_data.get("class"),
    #         convenient_dates=student_data.get("convenient_dates"),
    #         computer=student_data.get("computer"),
    #         email=student_data.get("email"),
    #         phone=student_data.get("phone"),
    #         course_id=student_data.get("course_id"),
    #         course_title=student_data.get("course_title"),
    #         registration_date=registration_date,
    #         status=status
    #     )

    #     db.session.add(student)

    # # Commit all records to the database
    # db.session.commit()
    # print("Students inserted successfully!")

    # visitors
    with open("mongo_exports/visits.json", "r", encoding="utf-8") as f:
        visitors_json = json.load(f)

    for visitor_data in visitors_json:
        # Parse timestamp
        timestamp_str = visitor_data.get("timestamp")
        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now(timezone.utc)

        # Parse date
        date_str = visitor_data.get("date")
        date_obj = datetime.fromisoformat(date_str).date() if date_str else None

        visitor = Visitor(
            ip_address=visitor_data.get("ip_address"),
            hostname=visitor_data.get("hostname"),
            user_agent_raw=visitor_data.get("user_agent_raw"),
            browser=visitor_data.get("browser"),
            browser_version=visitor_data.get("browser_version"),
            os=visitor_data.get("os"),
            os_version=visitor_data.get("os_version"),
            device=visitor_data.get("device"),
            is_mobile=visitor_data.get("is_mobile", False),
            is_tablet=visitor_data.get("is_tablet", False),
            is_pc=visitor_data.get("is_pc", False),
            is_bot=visitor_data.get("is_bot", False),
            referrer=visitor_data.get("referrer"),
            path=visitor_data.get("path"),
            timestamp=timestamp,
            date=date_obj,
            time=visitor_data.get("time")
        )

        db.session.add(visitor)

    # Commit all records
    db.session.commit()
    print("Visitors inserted successfully!")