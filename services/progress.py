import json
import os
import time
from datetime import datetime


def _progress_path(task_id):
    return f"task_{task_id}.progress"


def _now_iso():
    # Sử dụng datetime.now() hoặc UTC tùy cấu hình hệ thống năm 2026
    return datetime.utcnow().isoformat() + 'Z'


def write_progress(
    task_id,
    phase,
    progress,
    message,
    total_chapters=None,
    completed_chapters=None,
    current_chapter=None,
    chapter_title=None,
    extra=None,
):
    path = _progress_path(task_id)
    extra = extra or {}

    # Đọc dữ liệu cũ để lấy start_time hoặc logs cũ nếu có
    start_time = time.time()
    existing_logs = []
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                start_time = old_data.get('extra', {}).get('start_time', time.time())
                existing_logs = old_data.get('extra', {}).get('logs', [])
        except Exception:
            pass

    extra['start_time'] = start_time

    # Tự động cập nhật nhật ký hệ thống (Logs) khi có tin nhắn mới hoặc chương mới
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] "
    if chapter_title and phase in ('DOWNLOAD', 'TRANSLATE'):
        log_msg += f"{message} -> {chapter_title}"
    else:
        log_msg += message

    if not existing_logs or existing_logs[-1] != log_msg:
        existing_logs.append(log_msg)
        # Giới hạn 20 logs gần nhất để tránh phình dung lượng file JSON
        extra['logs'] = existing_logs[-20:]
    else:
        extra['logs'] = existing_logs

    # Tính toán ETA tự động (Thời gian ước tính còn lại)
    eta_str = "Đang tính..."
    if total_chapters and completed_chapters and completed_chapters > 0:
        elapsed = time.time() - start_time
        chapters_left = total_chapters - completed_chapters
        if chapters_left <= 0:
            eta_str = "00:00"
        else:
            time_per_chapter = elapsed / completed_chapters
            total_seconds_left = int(chapters_left * time_per_chapter)
            mins, secs = divmod(total_seconds_left, 60)
            eta_str = f"{mins:02d}:{secs:02d} còn lại"
    extra['eta'] = eta_str

    payload = {
        'status': 'processing' if phase not in ('DONE', 'ERROR') else ('done' if phase == 'DONE' else 'error'),
        'phase': phase,
        'progress': int(progress),
        'message': message,
        'total_chapters': total_chapters,
        'completed_chapters': completed_chapters,
        'current_chapter': current_chapter,
        'chapter_title': chapter_title,
        'updated_at': _now_iso(),
        'extra': extra,
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)
    return payload


def read_progress(task_id):
    path = _progress_path(task_id)
    defaults = {
        'status': 'processing',
        'phase': 'INIT',
        'progress': 0,
        'message': 'Đang khởi tạo...',
        'total_chapters': None,
        'completed_chapters': None,
        'current_chapter': None,
        'chapter_title': None,
        'updated_at': None,
        'extra': {'logs': [], 'eta': '--:--'},
    }
    if not os.path.exists(path):
        return defaults

    try:
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
            defaults.update(payload)
            return defaults
    except Exception:
        return defaults