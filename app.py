"""
SafeSend - Main Application
التطبيق الرئيسي
"""

import os
from dotenv import load_dotenv
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///nexus_dev.db")
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask, request, jsonify
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_talisman import Talisman
from flask_cors import CORS
from src.api.middleware import setup_middleware, limiter
import structlog

logger = structlog.get_logger(__name__)

app = Flask(__name__)

# Load config
app.config.from_object('src.app.models.config.DevelopmentConfig')
app.config['RATELIMIT_STORAGE_URI'] = 'redis://localhost:6379'
app.config['RATELIMIT_STRATEGY'] = "fixed-window"
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

app.config['SECRET_KEY'] = app.config.get('SECRET_KEY', 'safesend-dev-secret-key-change-in-production')

# Security: Cookie settings
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize CSRF Protection
csrf = CSRFProtect(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize Talisman for HTTPS/HSTS security headers
# In production: Talisman(app, force_https=True)
# In development: force_https=False
talisman = Talisman(
    app,
    force_https=False,
    strict_transport_security_preload=True,  # True in production
    strict_transport_security=True,
    strict_transport_security_max_age=31536000,
    strict_transport_security_include_subdomains=True,
    session_cookie_secure=True,
    content_security_policy={
        'default-src': "'self'",
        'style-src': ["'self'", "'unsafe-inline'", 'fonts.googleapis.com'],
        'font-src': ["'self'", 'fonts.gstatic.com'],
        'script-src': ["'self'", "'unsafe-inline'", 'cdnjs.cloudflare.com'],
        'img-src': ["'self'", 'data:'],
    }
)

# Setup middleware (includes rate limiter + security headers)
setup_middleware(app)

# Exempt API from CSRF for token-based auth (JWT handles this)
# CSRF exempt moved after blueprint registration

# Route to get CSRF token for frontend
@app.route('/api/v1/csrf-token', methods=['GET'])
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})

# Register blueprints
from src.api.v1.auth import auth_bp
from src.api.v1.admin import admin_bp
from src.api.v1.users import users_bp
from src.api.v1.files import files_bp
from src.api.v1.payments import payments_bp
from src.api.v1.messages import messages_bp
from src.api.v1.disputes import disputes_bp
from src.services.metrics import metrics_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(users_bp)
app.register_blueprint(files_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(disputes_bp)

# Exempt API blueprints from CSRF (use JWT instead)
csrf.exempt(auth_bp)
csrf.exempt(admin_bp)
csrf.exempt(users_bp)
csrf.exempt(files_bp)
csrf.exempt(payments_bp)
csrf.exempt(messages_bp)
csrf.exempt(disputes_bp)
app.register_blueprint(metrics_bp)

logger.info("app.started", blueprints=[bp.name for bp in app.blueprints.values()])

if __name__ == '__main__':
    app.run(debug=True)
