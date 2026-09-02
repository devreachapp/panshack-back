from flask import Flask, flash, send_file
from flask_migrate import Migrate
from flask_mail import Mail

from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from flask import Flask, request, redirect, send_from_directory,  render_template_string,render_template
from app.models import User
from config import Config
from flask_dance.contrib.google import make_google_blueprint
from flask_dance.contrib.facebook import make_facebook_blueprint
from flask_dance.consumer.storage import MemoryStorage

from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_login import current_user,login_user
from .extensions import db, login  # ✅ use from extensions

from flask_dance.consumer import oauth_authorized
from werkzeug.exceptions import RequestEntityTooLarge

from flask_session import Session

from flask_wtf.csrf import CSRFProtect

import jwt

import logging 

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from datetime import timedelta

import requests
FIXIE_URL = os.getenv("FIXIE_URL")

PROXIES = {
    "http": FIXIE_URL,
    "https": FIXIE_URL,
}


migrate = Migrate()
mail = Mail()
moment = Moment()


csrf = CSRFProtect()

login.login_view = '/login'


#logging.basicConfig(level=logging.DEBUG)


MAX_FILE_SIZE = 100 * 1024 * 1024  # 50 MB



SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 1800,  # Reconnect after 30 min
    'pool_timeout': 10

}



#UPLOAD_FOLDER = 'C:/Users/DELL/Documents/My Dev Files/cobiz/uploads' 

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")

#UPLOAD_FOLDER = "/data/business_assets"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USER_FOLDER='user_folders'



from celery import Celery


celery = Celery(__name__) 

import os, random, string, subprocess, uuid

def convert_to_webm(input_file, upload_folder):
    """Convert MP4 to WebM and return the new file path."""
    if not input_file.endswith(".mp4"):
        return input_file  # no conversion needed

    # Create a unique name for output file
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}.webm"
    output_file = os.path.join(upload_folder, unique_name)

    # Run ffmpeg conversion
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c:v", "libvpx-vp9",
        "-b:v", "1M",
        "-c:a", "libopus",
        output_file
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Converted {input_file} -> {output_file}")

        # Optional: delete old MP4
        if os.path.exists(input_file):
            os.remove(input_file)

        return output_file
    except subprocess.CalledProcessError as e:
        print(f"❌ Conversion failed: {e}")
        return input_file  # fallback to original


import sys

from flask_cors import CORS

from flask_dance.consumer.requests import OAuth2Session
from datetime import datetime, timedelta
# Override the session used by Flask-Dance to set timeouts
class TimeoutOAuth2Session(OAuth2Session):
    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", 10)  # 10 seconds timeout
        return super().request(method, url, **kwargs)
SECRET_KEY = 'nobemistake9ice'
from flask import redirect


from flask_dance.consumer import oauth_authorized

def create_app(config_class=Config):
    app = Flask(__name__, static_folder="static")

    app.config.from_object(config_class)




    CORS(app,resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",  # Vite default port
                "http://localhost:8080",  # CRA / Next.js default port
                "http://10.210.205.29:8080/",
                "https://justlink.app",
                "https://www.justlink.app",
                "https://swift-trade-hub.onrender.com/",
            ],
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        }
    },
    supports_credentials=True,)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.config["JWT_SECRET_KEY"] = "nobemistake9ice"
    JWTManager(app)


    app.config["SESSION_TYPE"] = "filesystem"  # saves sessions on server filesystem
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 4  # 4 hours
    Session(app)
    
    # API routes here
    # app.register_blueprint(auth_bp, url_prefix="/api")

    # ---------------------------
    # Serve React App (frontend)
    # ---------------------------

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        # Protect API routes
        if path.startswith("api"):
            return jsonify({"error": "Invalid API path"}), 404

        static_dir = app.static_folder
        
        # Strip leading 'static/' if request passed through static_url_path
        clean_path = path[7:] if path.startswith("static/") else path

        # Check if the requested file exists inside static directory
        file_path = os.path.join(static_dir, clean_path)
        if clean_path != "" and os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(static_dir, clean_path)

        # Check if index.html exists before serving
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return send_from_directory(static_dir, "index.html")

        return jsonify({
            "status": "error",
            "message": "Front-end build missing. Run 'npm run build' in front-end directory."
        }), 404
    @app.route("/download/ea")
    def download_ea():
        return send_file(
            "ea/signalExecutorEA.ex5",
            as_attachment=True,
            download_name="SignalExecutorEA.ex5"
        )
    @app.route('/static/uploads/<filename>')
    def serve_uploaded_file(filename):
        upload_dir = os.path.join(app.root_path, 'static', 'uploads')
        return send_from_directory(upload_dir, filename)

    @app.route("/ads.txt")
    def ads_txt():
        ads_path = os.path.join(os.path.dirname(__file__), "ads")
        return send_from_directory(ads_path, "ads.txt")
    
    @app.route("/google-success")
    def google_success():
        # React will handle everything from here
        return send_from_directory(app.static_folder, "index.html")



    app.config['WTF_CSRF_ENABLED'] = False  

    from flask_wtf.csrf import generate_csrf

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf())

    # Initialize extensions
    # 1. Initialize other extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login.init_app(app)
    moment.init_app(app)
    csrf.init_app(app) 


    from flask import session, request

    @app.errorhandler(413)
    @app.errorhandler(RequestEntityTooLarge)
    def app_handle_413(e):
        flash("File too big, max of 50MB for this file")
        return redirect(url_for('main.post_rewards'))
    
        
    @app.before_request
    def log_all_requests():
        print("🛰️  Incoming:", request.path)

    
    @app.before_request
    def before_request():
        if not request.is_secure and not app.debug:
            return redirect(request.url.replace("http://", "https://"))
    #app.config["OAUTHLIB_INSECURE_TRANSPORT"] = True  # for localhost testing only
    

    # 2. Set session config BEFORE calling session.init_app(app)

    #app.config['SESSION_SQLALCHEMY'] = db
    
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'session:'
    app.config['SECURITY_PASSWORD_SALT'] = 'lover'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    app.config['PROTECTED_FILES_DIR'] = os.path.abspath('./protected_files')
    app.config['DOWNLOAD_TTL_SECONDS'] = 16 * 3600  # 24h link

    # ------------------- BLUEPRINT REGISTRATION -------------------

    session_dir = os.path.join(app.root_path, 'flask_session')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    app.config['SESSION_FILE_DIR'] = session_dir

    if not os.access(session_dir, os.W_OK):
        print(f"❌ Session directory {session_dir} is not writable!")


    for view_func in app.view_functions:
        csrf.exempt(view_func)


    # Setup Google OAuth

    # 3. Now initialize Flask-Session
    

    # Make upload folders if they don't exist

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    if not os.path.exists(app.config['UPLOAD_USER_FOLDER']):
        os.makedirs(app.config['UPLOAD_USER_FOLDER'])

    @app.route('/sw.js')
    def serve_sw():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js', mimetype='application/javascript')

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "message": str(e)}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Server error", "message": str(e)}), 500

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api")


    from app.crypto import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix="/api")


    from app.menu import bp as menu_bp
    app.register_blueprint(menu_bp,url_prefix="/api")


    from app.wallet import bp as wallet_bp
    app.register_blueprint(wallet_bp,url_prefix="/api")

    from app.notification import bp as notifications_bp
    app.register_blueprint(notifications_bp,url_prefix="/api")

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp,url_prefix="/api")

    return app