import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import DATABASE_PATH, BASE_DIR

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with required tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            storage_limit INTEGER DEFAULT 5368709120, -- 5GB in bytes
            plan TEXT DEFAULT 'free'
        )
    ''')
    
    # Files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_type TEXT,
            mime_type TEXT,
            folder TEXT DEFAULT '',
            is_public BOOLEAN DEFAULT 0,
            public_token TEXT UNIQUE,
            download_count INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Shared links table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
        )
    ''')

    # Try to add folder column if table exists but column doesn't
    try:
        cursor.execute('ALTER TABLE files ADD COLUMN folder TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def create_user(username, email, password):
    """Create a new user"""
    conn = get_db()
    cursor = conn.cursor()
    
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        user_id = cursor.lastrowid
        
        # Create user's upload directory
        user_upload_dir = os.path.join(BASE_DIR, 'uploads', str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    """Get user by username"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def verify_password(username, password):
    """Verify user password"""
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

def get_file_by_id(file_id, user_id=None):
    """Get file by ID, optionally check ownership"""
    conn = get_db()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute(
            'SELECT * FROM files WHERE id = ? AND user_id = ?',
            (file_id, user_id)
        )
    else:
        cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
    
    file = cursor.fetchone()
    conn.close()
    return file

def get_user_storage_usage(user_id):
    """Get total storage usage for a user"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT COALESCE(SUM(file_size), 0) as total_size FROM files WHERE user_id = ?',
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result['total_size'] if result else 0

def delete_file(file_id, user_id):
    """Delete a file"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get file info before deleting
    file = get_file_by_id(file_id, user_id)
    if not file:
        return False
    
    # Delete from database
    cursor.execute('DELETE FROM files WHERE id = ? AND user_id = ?', (file_id, user_id))
    
    # Delete physical file
    try:
        os.remove(file['filepath'])
    except OSError:
        pass
    
    conn.commit()
    conn.close()
    return True

def create_share_token(file_id):
    """Create a share token for a file"""
    import uuid
    token = str(uuid.uuid4())
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Update file to be public
    cursor.execute(
        'UPDATE files SET is_public = 1, public_token = ? WHERE id = ?',
        (token, file_id)
    )
    
    conn.commit()
    conn.close()
    return token

def disable_share_token(file_id, user_id):
    """Disable sharing for a file"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        'UPDATE files SET is_public = 0, public_token = NULL WHERE id = ? AND user_id = ?',
        (file_id, user_id)
    )
    
    conn.commit()
    conn.close()

def get_public_file(token):
    """Get public file by token"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM files WHERE public_token = ? AND is_public = 1',
        (token,)
    )
    file = cursor.fetchone()
    conn.close()
    return file


def add_file(user_id, filename, original_filename, filepath, file_size, file_type, mime_type, folder=''):
    """Add file record to database"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO files (user_id, filename, original_filename, filepath, 
                          file_size, file_type, mime_type, folder)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, filename, original_filename, filepath, file_size, file_type, mime_type, folder))

    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id


def get_user_files(user_id, folder=''):
    """Get files for a user, optionally filtered by folder"""
    conn = get_db()
    cursor = conn.cursor()

    if folder:
        cursor.execute(
            '''SELECT * FROM files WHERE user_id = ? AND folder = ? 
               ORDER BY uploaded_at DESC''',
            (user_id, folder)
        )
    else:
        cursor.execute(
            'SELECT * FROM files WHERE user_id = ? ORDER BY uploaded_at DESC',
            (user_id,)
        )

    files = cursor.fetchall()
    conn.close()
    return files
