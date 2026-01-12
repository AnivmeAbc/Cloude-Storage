from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, abort, Response
import os
import uuid
from werkzeug.utils import secure_filename
import mimetypes
from typing import Union

from config import *
from database import *
from utils import allowed_file, get_file_icon, format_file_size, is_image_file

from PIL import Image
import io

app = Flask(__name__)
app.config.from_object('config')

# Initialize database
with app.app_context():
    init_db()


@app.before_request
def before_request():
    """Check if user is logged in for protected routes"""
    protected_routes = ['dashboard', 'upload', 'download', 'delete', 'share']
    if request.endpoint in protected_routes and 'user_id' not in session:
        return redirect(url_for('auth_page'))


@app.route('/')
def index():
    """Home page - redirect to auth if not logged in, else dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth_page'))


@app.route('/auth', methods=['GET', 'POST'])
def auth_page():
    """Authentication page (login/register)"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'login':
            username = request.form.get('username')
            password = request.form.get('password')

            user = verify_password(username, password)
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            else:
                return render_template('auth.html', error='Invalid credentials')

        elif action == 'register':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if password != confirm_password:
                return render_template('auth.html', error='Passwords do not match')

            user_id = create_user(username, email, password)
            if user_id:
                session['user_id'] = user_id
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                return render_template('auth.html', error='Username or email already exists')

    return render_template('auth.html')


@app.route('/create-folder', methods=['POST'])
def create_folder():
    """Create a new folder"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    folder_name = request.form.get('folder_name', '').strip()

    print(f"DEBUG: Creating folder. User ID: {user_id}, Folder name: '{folder_name}'")

    if not folder_name:
        return jsonify({'error': 'Folder name is required'}), 400

    # Sanitize folder name
    folder_name = secure_filename(folder_name)

    # Create folder path
    folder_path = os.path.join(UPLOAD_FOLDER, str(user_id), folder_name)

    print(f"DEBUG: Folder path: {folder_path}")
    print(f"DEBUG: Upload folder base: {UPLOAD_FOLDER}")

    try:
        # Check if folder already exists
        if os.path.exists(folder_path):
            return jsonify({'error': 'Folder already exists'}), 400

        # Create folder
        os.makedirs(folder_path, exist_ok=True)

        print(f"DEBUG: Folder created successfully")

        return jsonify({'success': True, 'folder_name': folder_name})
    except Exception as e:
        print(f"DEBUG: Error creating folder: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create folder: {str(e)}'}), 500


@app.route('/get-folders')
def get_folders():
    """Get list of folders for current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    user_dir = os.path.join(UPLOAD_FOLDER, str(user_id))

    print(f"DEBUG: Getting folders for user {user_id}")
    print(f"DEBUG: User directory: {user_dir}")
    print(f"DEBUG: Directory exists: {os.path.exists(user_dir)}")

    folders = []
    if os.path.exists(user_dir):
        try:
            # Get all directories
            for item in os.listdir(user_dir):
                item_path = os.path.join(user_dir, item)
                if os.path.isdir(item_path):
                    folders.append(item)

            print(f"DEBUG: Found folders: {folders}")
        except Exception as e:
            print(f"DEBUG: Error listing folders: {str(e)}")
    else:
        print(f"DEBUG: User directory does not exist, creating it")
        try:
            os.makedirs(user_dir, exist_ok=True)
        except Exception as e:
            print(f"DEBUG: Error creating user directory: {str(e)}")

    return jsonify({'folders': folders})


@app.route('/dashboard')
def dashboard():
    """Main dashboard with file list"""
    user_id = session['user_id']
    username = session['username']

    # Get current folder from query parameter
    current_folder = request.args.get('folder', '')

    print(f"DEBUG: Loading dashboard. User: {user_id}, Folder: '{current_folder}'")

    # Get user files for current folder
    files = get_user_files(user_id, current_folder)

    print(f"DEBUG: Found {len(files)} files for folder '{current_folder}'")

    # Calculate storage usage
    user = get_user_by_id(user_id)
    used_storage = get_user_storage_usage(user_id)
    total_storage = user['storage_limit']
    storage_percentage = (used_storage / total_storage * 100) if total_storage > 0 else 0

    # Format file data for template
    formatted_files = []
    for file in files:
        # Check if file is an image
        is_image = is_image_file(file['file_type'], file['mime_type'])

        # Generate image URL with cache busting
        image_url = None
        if is_image:
            image_url = url_for('image_preview', file_id=file['id'])

        formatted_files.append({
            'id': file['id'],
            'name': file['original_filename'],
            'size': format_file_size(file['file_size']),
            'type': file['file_type'],
            'icon': get_file_icon(file['file_type']),
            'uploaded_at': file['uploaded_at'],
            'is_public': bool(file['is_public']),
            'public_token': file['public_token'],
            'is_image': is_image,
            'image_url': image_url,
            'folder': file['folder'] if 'folder' in file else ''
        })

    return render_template('dashboard.html',
                           username=username,
                           files=formatted_files,
                           used_storage=format_file_size(used_storage),
                           total_storage=format_file_size(total_storage),
                           storage_percentage=min(storage_percentage, 100),
                           current_folder=current_folder)


@app.route('/thumbnail/<int:file_id>')
def thumbnail(file_id):
    """Generate thumbnail for image files"""
    user_id = session.get('user_id')

    # Check if user owns the file or file is public
    file = get_file_by_id(file_id)
    if not file:
        abort(404)

    if file['user_id'] != user_id and not file['is_public']:
        abort(403)

    # Check if file is an image
    if not is_image_file(file['file_type'], file['mime_type']):
        abort(404)

    # Check if thumbnail already exists
    thumb_path = file['filepath'] + '.thumb'
    if os.path.exists(thumb_path):
        return send_file(thumb_path)

    try:
        # Create thumbnail
        with Image.open(file['filepath']) as img:
            # Calculate thumbnail size
            img.thumbnail((300, 300))

            # Save thumbnail to bytes
            thumb_bytes = io.BytesIO()
            img_format = img.format if img.format else 'JPEG'
            img.save(thumb_bytes, format=img_format)
            thumb_bytes.seek(0)

            # Save thumbnail to disk for caching
            with open(thumb_path, 'wb') as f:
                f.write(thumb_bytes.getbuffer())

            return send_file(thumb_path, mimetype='image/jpeg')
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        # Fallback to original image
        return send_file(file['filepath'])


@app.route('/upload', methods=['POST'])
def upload():
    """Handle file uploads"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    user = get_user_by_id(user_id)

    # Get folder from form data
    folder = request.form.get('folder', '')

    print(f"DEBUG: Uploading file. User: {user_id}, Folder: '{folder}'")

    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Validate file
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    # Check storage limit
    used_storage = get_user_storage_usage(user_id)
    if used_storage + file_size > user['storage_limit']:
        return jsonify({'error': 'Storage limit exceeded'}), 400

    # Save file
    original_filename = file.filename
    if original_filename is None:
        return jsonify({'error': 'Invalid filename'}), 400

    secured_filename = secure_filename(original_filename)
    file_extension = os.path.splitext(secured_filename)[1].lower()
    file_type = file_extension[1:] if file_extension else 'unknown'

    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"

    # Create user upload directory with optional folder
    if folder:
        user_upload_dir = os.path.join(UPLOAD_FOLDER, str(user_id), folder)
    else:
        user_upload_dir = os.path.join(UPLOAD_FOLDER, str(user_id))

    filepath = os.path.join(user_upload_dir, unique_filename)

    print(f"DEBUG: Saving file to: {filepath}")

    # Ensure directory exists
    os.makedirs(user_upload_dir, exist_ok=True)

    # Save file
    try:
        file.save(filepath)
    except Exception as e:
        print(f"ERROR: Failed to save file: {e}")
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

    # Get MIME type
    mime_type = mimetypes.guess_type(secured_filename)[0] or 'application/octet-stream'

    # Add to database with folder info
    file_id = add_file(user_id, unique_filename, secured_filename,
                       filepath, file_size, file_type, mime_type, folder)

    print(f"DEBUG: File saved with ID: {file_id}")

    return jsonify({
        'success': True,
        'file_id': file_id,
        'filename': secured_filename,
        'file_size': format_file_size(file_size),
        'is_image': is_image_file(file_type, mime_type),
        'folder': folder
    })


@app.route('/download/<int:file_id>')
def download(file_id: int) -> Union[Response, None]:
    """Download a file"""
    user_id = session.get('user_id')

    # Check if user owns the file or file is public
    file = get_file_by_id(file_id)
    if not file:
        abort(404)

    if file['user_id'] != user_id and not file['is_public']:
        abort(403)

    # Increment download count if public
    if file['is_public']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE files SET download_count = download_count + 1 WHERE id = ?',
            (file_id,)
        )
        conn.commit()
        conn.close()

    return send_file(
        file['filepath'],
        as_attachment=True,
        download_name=file['original_filename']
    )


@app.route('/delete/<int:file_id>', methods=['POST'])
def delete(file_id):
    """Delete a file"""
    user_id = session['user_id']

    if delete_file(file_id, user_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'File not found or permission denied'}), 404


@app.route('/share/<int:file_id>', methods=['POST', 'DELETE'])
def share(file_id):
    """Share or unshare a file"""
    user_id = session['user_id']

    if request.method == 'POST':
        # Create share token
        token = create_share_token(file_id)
        share_url = url_for('public_file', token=token, _external=True)
        return jsonify({'success': True, 'share_url': share_url, 'token': token})

    elif request.method == 'DELETE':
        # Disable sharing
        disable_share_token(file_id, user_id)
        return jsonify({'success': True})


@app.route('/public/<token>')
def public_file(token):
    """Public file access"""
    file = get_public_file(token)
    if not file:
        abort(404)

    return render_template('share.html', file=file, token=token)


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('auth_page'))


@app.route('/api/storage')
def api_storage():
    """API endpoint for storage info"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    user = get_user_by_id(user_id)
    used_storage = get_user_storage_usage(user_id)
    total_storage = user['storage_limit']

    return jsonify({
        'used': used_storage,
        'total': total_storage,
        'percentage': (used_storage / total_storage * 100) if total_storage > 0 else 0,
        'used_formatted': format_file_size(used_storage),
        'total_formatted': format_file_size(total_storage)
    })


@app.route('/image/<int:file_id>')
def image_preview(file_id):
    """Serve image file for preview"""
    user_id = session.get('user_id')

    # Check if user owns the file or file is public
    file = get_file_by_id(file_id)
    if not file:
        abort(404)

    if file['user_id'] != user_id and not file['is_public']:
        abort(403)

    # Check if file is an image
    if not is_image_file(file['file_type'], file['mime_type']):
        abort(404)

    # Add cache control headers
    response = send_file(file['filepath'])
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
