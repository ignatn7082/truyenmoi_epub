


import os
from flask import Blueprint, jsonify, url_for

from services.progress import read_progress


status_bp = Blueprint("status", __name__)

@status_bp.route('/status/<task_id>')
def check_status(task_id):
    status_file = f"task_{task_id}.status"
    progress_data = read_progress(task_id)

    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            content = f.read().strip()
            if content.startswith('DONE|'):
                filepath = content.split('|', 1)[1]
                filename = os.path.basename(filepath)
                return jsonify({
                    'status': 'done',
                    'download_url': url_for('download.download_file', filename=filename),
                    'filename': filename,
                    'progress': 100,
                    'message': 'Hoàn thành',
                    'total_chapters': progress_data.get('total_chapters')
                })
            elif content.startswith('ERROR|'):
                return jsonify({'status': 'error', 'message': content.split('|', 1)[1]})

    return jsonify({
        'status': 'processing',
        'progress': progress_data.get('progress', 0),
        'message': progress_data.get('message', 'Đang khởi tạo...'),
        'phase': progress_data.get('phase', 'INIT'),
        'total_chapters': progress_data.get('total_chapters')
    })
