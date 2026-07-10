from flask import Flask
from routes.home import home_bp
from routes.convert import convert_bp
from routes.status import status_bp
from routes.download import download_bp

app = Flask(__name__)

app.register_blueprint(home_bp)
app.register_blueprint(convert_bp)
app.register_blueprint(status_bp)
app.register_blueprint(download_bp)

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)