# ==========================================
# app.py - Main Entry Point
# ==========================================

import os
from flask import Flask, session, redirect, send_from_directory
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

from utils.db import init_db
from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
csrf = CSRFProtect(app)

# Initialize Database
init_db()

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)

@app.route('/img/<path:filename>')
def serve_img(filename):
    return send_from_directory('img', filename)

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    app.run(debug=debug_mode)
