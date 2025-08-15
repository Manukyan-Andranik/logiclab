from flask_mail import Mail
from data_manager import *
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

mail = Mail()