"""
routes/convert.py

Nhận link truyện từ UI, khởi chạy tải EPUB ở background thread, trả về
job_id để templates/index.html poll tiến trình qua routes/status.py.

Hỗ trợ 2 nguồn:
  - metruyenchuvn.com (và site cùng theme)  -> services/metruyenchuvn_scraper.py
  - các nguồn khác (vd truyenmoiss.org)      -> services gốc của project (nếu có)

Nếu project gốc đã có services/scraper.py (bản cũ cho truyenmoiss.org), giữ
nguyên import đó ở nhánh else bên dưới - chỉ cần bỏ comment và sửa tên hàm
cho khớp với code cũ của bạn.
"""

import os
import re
import threading
import uuid

from flask import Blueprint, jsonify, request

from services.sources import metruyenchu as mtc

convert_bp = Blueprint("convert", __name__)

OUTPUT_DIR = os.path.join(os.getcwd(), "generated_epubs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# job_id -> {"status": "running"|"done"|"error", "done": int, "total": int|None,
#            "current_title": str, "error": str|None, "file": str|None, "book_title": str|None}
JOBS: dict[str, dict] = {}


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\-. ]+", "_", name, flags=re.UNICODE).strip("_ ")
    return name or "truyen"


def _run_job(job_id: str, url: str):
    job = JOBS[job_id]

    def on_progress(done, total, title):
        job["done"] = done
        job["total"] = total
        job["current_title"] = title

    try:
        if mtc.is_supported(url):
            # Lấy thông tin sách trước để có tên file + cập nhật UI sớm
            import requests
            session = requests.Session()
            book_info = mtc.get_book_info(url, session)
            job["book_title"] = book_info["title"]
            job["total"] = job["total"] or book_info.get("total_chapters") or len(
                book_info.get("known_chapters") or []
            ) or None

            filename = f"{_safe_filename(book_info['title'])}-{job_id[:8]}.epub"
            output_path = os.path.join(OUTPUT_DIR, filename)

            chapters = mtc.crawl_all_chapters(
                book_info, session, delay=0.15, workers=8, on_progress=on_progress
            )
            mtc.build_epub(book_info, chapters, output_path, session)

            job["file"] = filename
            job["status"] = "done"
        else:
            # TODO: gọi scraper gốc của project cho truyenmoiss.org tại đây, ví dụ:
            # from services.scraper import download_book as download_book_truyenmoiss
            # download_book_truyenmoiss(url, ...)
            job["status"] = "error"
            job["error"] = (
                "Nguồn này chưa được hỗ trợ trong bản addon. "
                "Hiện chỉ hỗ trợ metruyenchuvn.com (và site cùng theme)."
            )
    except Exception as e:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = str(e)


@convert_bp.route("/convert", methods=["POST"])
def convert():
    data = request.get_json(silent=True) or request.form
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Thiếu link truyện."}), 400

    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        "status": "running",
        "done": 0,
        "total": None,
        "current_title": "",
        "error": None,
        "file": None,
        "book_title": None,
        "url": url,
    }

    thread = threading.Thread(target=_run_job, args=(job_id, url), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})
