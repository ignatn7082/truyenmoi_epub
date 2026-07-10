  
import os
from flask import Blueprint, send_file
from config import UPLOAD_FOLDER

download_bp = Blueprint("download", __name__)

@download_bp.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)
    