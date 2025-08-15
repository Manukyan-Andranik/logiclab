from flask import Flask
from flask_mail import Mail
from routes import site_routes, user_routes, admin_routes, DataManager

from utils import load_env
import os
from urllib.parse import quote_plus

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Mail config
MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, _ = load_env()
app.config.update(
    MAIL_SERVER=MAIL_SERVER,
    MAIL_PORT=MAIL_PORT,
    MAIL_USE_TLS=MAIL_USE_TLS,
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER=MAIL_DEFAULT_SENDER
)
mail = Mail(app)

# DB config
escaped_user = quote_plus(os.getenv('MONGO_USERNAME'))
escaped_pass = quote_plus(os.getenv('MONGO_PASSWORD'))
URI = f"mongodb+srv://{escaped_user}:{escaped_pass}@cluster0.ckpsnux.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
app.config['MONGO_URI'] = URI

# Share DataManager globally
from data_manager import set_global_data_manager
DATA_MANAGER = DataManager(app, URI)
set_global_data_manager(DATA_MANAGER)

# Register Blueprints
app.register_blueprint(site_routes)
app.register_blueprint(user_routes)
app.register_blueprint(admin_routes)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
