import sqlite3
import os
from datetime import datetime


def get_db_connection():
    conn = sqlite3.connect('cloud_storage.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    # Создание таблицы пользователей
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Создание таблицы файлов
    conn.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL,
            is_public BOOLEAN DEFAULT FALSE,
            share_token TEXT UNIQUE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()


def create_user(username, email, password):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, password)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    conn.close()
    return user


def create_file(filename, original_filename, file_size, user_id, share_token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO files 
        (filename, original_filename, file_size, user_id, share_token) 
        VALUES (?, ?, ?, ?, ?)''',
        (filename, original_filename, file_size, user_id, share_token)
    )
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id


def get_user_files(user_id):
    conn = get_db_connection()
    files = conn.execute(
        'SELECT * FROM files WHERE user_id = ? ORDER BY upload_date DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return files


def get_file_by_id(file_id):
    conn = get_db_connection()
    file = conn.execute(
        'SELECT * FROM files WHERE id = ?', (file_id,)
    ).fetchone()
    conn.close()
    return file


def get_file_by_token(share_token):
    conn = get_db_connection()
    file = conn.execute(
        'SELECT * FROM files WHERE share_token = ? AND is_public = TRUE',
        (share_token,)
    ).fetchone()
    conn.close()
    return file


def delete_file(file_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
    conn.commit()
    conn.close()


def make_file_public(file_id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE files SET is_public = TRUE WHERE id = ?',
        (file_id,)
    )
    conn.commit()
    conn.close()


def get_user_stats(user_id):
    conn = get_db_connection()

    # Количество файлов
    total_files = conn.execute(
        'SELECT COUNT(*) FROM files WHERE user_id = ?',
        (user_id,)
    ).fetchone()[0]

    # Общий размер файлов
    total_size = conn.execute(
        'SELECT COALESCE(SUM(file_size), 0) FROM files WHERE user_id = ?',
        (user_id,)
    ).fetchone()[0]

    conn.close()
    return total_files, total_size