import os
from datetime import timedelta

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Secret key for sessions
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

# Database path
DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'database.db')

# Upload settings
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx',
    'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', 'mp3', 'mp4',
    'avi', 'mov', 'wmv', 'flv', 'webm', 'csv', 'json', 'xml'
}
DANGEROUS_EXTENSIONS = {'exe', 'bat', 'cmd', 'sh', 'ps1', 'vbs', 'js', 'jar'}

# Session settings
PERMANENT_SESSION_LIFETIME = timedelta(days=7)
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True

# Storage limits (in bytes)
STORAGE_LIMITS = {
    'free': 5 * 1024 * 1024 * 1024,  # 5GB
    'premium': 50 * 1024 * 1024 * 1024  # 50GB
}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
