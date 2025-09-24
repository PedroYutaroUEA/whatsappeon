from flask import Flask
from app.routes import groups_bp, users_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(users_bp)
    app.register_blueprint(groups_bp)

    return app
