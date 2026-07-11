import os

from flask import Blueprint, abort, send_from_directory

from routes.convert import JOBS, OUTPUT_DIR

download_bp = Blueprint("download", __name__)


@download_bp.route("/download/<job_id>")
def download(job_id):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "done" or not job.get("file"):
        abort(404)

    file_path = os.path.join(OUTPUT_DIR, job["file"])
    if not os.path.exists(file_path):
        abort(404)

    download_name = f"{job.get('book_title') or 'truyen'}.epub"
    return send_from_directory(
        OUTPUT_DIR, job["file"], as_attachment=True, download_name=download_name
    )
