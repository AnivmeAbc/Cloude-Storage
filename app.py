from aiogram.types import file
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from functools import wraps

import database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Check auth
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# init db
def init_app():
    database.init_db()
    #create folder for uploads
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

# routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # checking user existence
        if database.get_user_by_username(username):
            flash('Имя пользователя уже существует')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user_id = database.create_user(username, email, hashed_password)

        if user_id:
            flash('Регистрация успешна! Войдите в систему.')
            return redirect(url_for('login'))
        else:
            flash('Ошибка при регистрации')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = database.get_user_by_username(username)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_files = database.get_user_files(session['user_id'])
    total_files, total_size = database.get_user_stats(session['user_id'])

    # take the last 5 files
    recent_files = user_files[:5] if user_files else []

    return render_template('dashboard.html',
                           files=recent_files,
                           total_files=total_files,
                           total_size=total_size)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            # Generate unique filename
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            file.save(file_path)
            file_size = os.path.getsize(file_path)

            # Generate token for sharing
            share_token = uuid.uuid4().hex[:16]

            database.create_file(
                unique_filename,
                filename,
                file_size,
                session['user_id'],
                share_token
            )

            flash('Файл успешно загружен!')
            return redirect(url_for('dashboard'))

    return render_template('upload.html')

@app.route('/files')
@login_required
def files():
    user_files = database.get_user_files(session['user_id'])
    return render_template('files.html', files=user_files)

@app.route('/download/<int:file_id>')
@login_required
def download(file_id):
    file = database.get_file_by_id(file_id)

    if not file:
        flash('Файл не найден')
        return redirect(url_for('dashboard'))

    # Checking file ownership
    if file['user_id'] != session['user_id'] and not file['is_public']:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file['filename'])
    return send_file(file_path, as_attachment=True, download_name=file['original_filename'])


@app.route('/delete/<int:file_id>')
@login_required
def delete(file_id):
    file = database.get_file_by_id(file_id)

    if not file or file['user_id'] != session['user_id']:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))

    # delete phis. file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file['filename'])
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete record from DB
    database.delete_file(file_id)

    flash('Файл успешно удален!')
    return redirect(url_for('files'))


@app.route('/share/<int:file_id>')
@login_required
def share(file_id):
    file = database.get_file_by_id(file_id)

    if not file or file['user_id'] != session['user_id']:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))

    database.make_file_public(file_id)

    share_url = url_for('shared_file', token=file['share_token'], _external=True)
    flash(f'Файл доступен по ссылке: {share_url}')
    return redirect(url_for('files'))


@app.route('/shared/<token>')
def shared_file(token):
    file = database.get_file_by_token(token)

    if not file:
        flash('Файл не найден или доступ закрыт')
        return redirect(url_for('login'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file['filename'])
    return send_file(file_path, as_attachment=True, download_name=file['original_filename'])


if __name__ == '__main__':
    init_app()
    app.run(debug=True, host='0.0.0.0', port=4321)