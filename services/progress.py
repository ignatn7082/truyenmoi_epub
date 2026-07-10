import json
import os


def _progress_path(task_id):
    return f"task_{task_id}.progress"


def write_progress(task_id, phase, progress, message, total_chapters=None):
    payload = {
        'phase': phase,
        'progress': int(progress),
        'message': message,
        'total_chapters': total_chapters,
    }
    with open(_progress_path(task_id), 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)


def read_progress(task_id):
    path = _progress_path(task_id)
    if not os.path.exists(path):
        return {'phase': 'INIT', 'progress': 0, 'message': 'Đang khởi tạo...', 'total_chapters': None}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'phase': 'INIT', 'progress': 0, 'message': 'Đang khởi tạo...', 'total_chapters': None}
