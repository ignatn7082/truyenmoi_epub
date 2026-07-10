


import os
from flask import Blueprint, jsonify, url_for

from services.progress import read_progress


status_bp = Blueprint("status", __name__)

@status_bp.route('/status/<task_id>')
def check_status(task_id):
    status_file = f"task_{task_id}.status"
    progress_data = read_progress(task_id)

    response = progress_data.copy()

    if os.path.exists(status_file):
        with open(status_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.startswith('DONE|'):
                filepath = content.split('|', 1)[1]
                filename = os.path.basename(filepath)
                response.update({
                    'status': 'done',
                    'progress': 100,
                    'message': 'Hoàn thành',
                    'download_url': url_for('download.download_file', filename=filename),
                    'filename': filename,
                })
            elif content.startswith('ERROR|'):
                response.update({
                    'status': 'error',
                    'message': content.split('|', 1)[1],
                })

    return jsonify(response)
