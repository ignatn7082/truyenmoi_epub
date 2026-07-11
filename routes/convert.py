import threading
import uuid
from flask import Blueprint, jsonify, request
from services.background import scan_and_create_epub
from services.sources.registry import get_crawler, get_supported_domains


convert_bp = Blueprint("convert", __name__)

@convert_bp.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url', '').strip()
    crawler = get_crawler(url)
    if not crawler:
        supported = ", ".join(get_supported_domains())
        return jsonify({'error': f'Chưa hỗ trợ nguồn này. Hiện hỗ trợ: {supported}'}), 400

    task_id = str(uuid.uuid4())[:8]
    novel_title, base_url = crawler.extract_novel_info(url)

    threading.Thread(
        target=scan_and_create_epub,
        args=(novel_title, base_url, task_id, crawler),
        daemon=True
    ).start()

    return jsonify({
        'task_id': task_id,
        'novel_title': novel_title,
        'message': f'Đang quét mục lục từ {crawler.name}...'
    })