"""
Masdhii22 Media Server
Server sederhana untuk menyimpan foto & video.
Jalankan: python app.py
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)  # Izinkan website (domain manapun) memanggil server ini

# Folder penyimpanan (relatif terhadap lokasi app.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Maksimal 150 MB per file
app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    # foto
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp',
    # video
    'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v'
}

# API Key sederhana (ubah sesuai keinginan)
# Kosongkan string jika tidak ingin memakai API Key
API_KEY = os.environ.get('MEDIA_API_KEY', 'masdhii22-secret')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_api_key():
    """Cek header X-API-Key. Return True jika valid atau API_KEY kosong."""
    if not API_KEY:
        return True
    key = request.headers.get('X-API-Key') or request.args.get('key')
    return key == API_KEY


@app.route('/')
def home():
    return jsonify({
        'service': 'Masdhii22 Media Server',
        'status': 'running',
        'endpoints': {
            'upload': 'POST /upload  (form-data: file)',
            'list': 'GET /list',
            'media': 'GET /media/<filename>',
            'delete': 'DELETE /delete/<filename>'
        }
    })


@app.route('/upload', methods=['POST'])
def upload_file():
    if not check_api_key():
        return jsonify({'success': False, 'error': 'API Key tidak valid'}), 401

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Tidak ada file (key harus "file")'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nama file kosong'}), 400

    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': 'Format tidak didukung. Gunakan: ' + ', '.join(sorted(ALLOWED_EXTENSIONS))
        }), 400

    original = secure_filename(file.filename)
    ext = original.rsplit('.', 1)[1].lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{unique}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        file.save(filepath)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Gagal menyimpan: {str(e)}'}), 500

    base_url = request.host_url.rstrip('/')
    file_url = f"{base_url}/media/{filename}"
    is_video = ext in {'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v'}

    return jsonify({
        'success': True,
        'filename': filename,
        'original_name': original,
        'url': file_url,
        'type': 'video' if is_video else 'image',
        'size': os.path.getsize(filepath)
    })


@app.route('/media/<filename>')
def serve_media(filename):
    # Keamanan dasar: cegah path traversal
    safe = secure_filename(filename)
    if safe != filename or '..' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    return send_from_directory(UPLOAD_FOLDER, safe)


@app.route('/list', methods=['GET'])
def list_files():
    if not check_api_key():
        return jsonify({'success': False, 'error': 'API Key tidak valid'}), 401

    files = []
    for f in sorted(os.listdir(UPLOAD_FOLDER), reverse=True):
        filepath = os.path.join(UPLOAD_FOLDER, f)
        if os.path.isfile(filepath):
            ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
            files.append({
                'filename': f,
                'url': f"{request.host_url.rstrip('/')}/media/{f}",
                'type': 'video' if ext in {'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v'} else 'image',
                'size': os.path.getsize(filepath)
            })
    return jsonify({'success': True, 'count': len(files), 'files': files})


@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    if not check_api_key():
        return jsonify({'success': False, 'error': 'API Key tidak valid'}), 401

    safe = secure_filename(filename)
    if safe != filename:
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, safe)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        os.remove(filepath)
        return jsonify({'success': True, 'message': f'{safe} dihapus'})
    return jsonify({'success': False, 'error': 'File tidak ditemukan'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Masdhii22 Media Server running on http://0.0.0.0:{port}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"API Key: {'aktif' if API_KEY else 'tidak dipakai'}")
    app.run(host='0.0.0.0', port=port, debug=False)
