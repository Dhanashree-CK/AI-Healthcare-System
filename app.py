from flask import Flask
from flask_cors import CORS
from routes import main_routes
from models import db
from prescription_routes import prescription_routes
from flask_mail import Mail # type: ignore

app = Flask(__name__)
app.secret_key = 'care-connect-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
CORS(app)

# MySQL Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root123@127.0.0.1:3306/healthcare_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# EMAIL CONFIGURATION
# -------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ccare5106@gmail.com'
app.config['MAIL_PASSWORD'] = 'sfqprppfgbqgjcuh'
app.config['MAIL_DEFAULT_SENDER'] = 'ccare5106@gmail.com'

mail = Mail(app)

# Register routes
app.register_blueprint(main_routes)
app.register_blueprint(prescription_routes, url_prefix="/prescription")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()   # creates table automatically
    app.run(host="0.0.0.0", port=5000, debug=True)