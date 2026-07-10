    
import threading
import uuid
from flask import Blueprint, jsonify, request
from services.background import scan_and_create_epub
from untils.parser import extract_novel_info
from untils.validator import is_valid_truyenmoiss_url


convert_bp = Blueprint("convert", __name__)

@convert_bp.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url', '').strip()
    if not is_valid_truyenmoiss_url(url):
        return jsonify({'error': 'Vui lòng nhập link hợp lệ từ truyenmoiss.org'}), 400

    task_id = str(uuid.uuid4())[:8]
    novel_title, base_url = extract_novel_info(url)
    
    # Chạy quét trong background
    threading.Thread(
        target=scan_and_create_epub, 
        args=(novel_title, base_url, task_id), 
        daemon=True
    ).start()

    return jsonify({
        'task_id': task_id,
        'novel_title': novel_title,
        'message': 'Đang quét mục lục...'
    })
