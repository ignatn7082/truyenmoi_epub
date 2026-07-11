from flask import Blueprint, jsonify

from routes.convert import JOBS

status_bp = Blueprint("status", __name__)


@status_bp.route("/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Không tìm thấy job."}), 404

    percent = None
    if job["total"]:
        percent = min(100, round(job["done"] * 100 / job["total"]))

    return jsonify({
        "status": job["status"],
        "done": job["done"],
        "total": job["total"],
        "percent": percent,
        "current_title": job["current_title"],
        "book_title": job["book_title"],
        "error": job["error"],
        "file": job["file"],
    })
