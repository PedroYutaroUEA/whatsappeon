from flask import Blueprint, request
from app.src.controllers import UsersController

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/create", methods=["POST"])
def register_user():
    """Rota para registrar usuários."""
    # user_controller.create_user()
    pass


@users_bp.route("/<username>/messages", methods=["POST, GET"])
def direct_messaging_handler(username: str):
    """Rota para gerar relatórios de issues."""
    user_controller = UsersController()

    if request.method == "POST":
        user_controller.send_message(username)
        pass
    elif request.method == "GET":
        # user_controller.query_message()
        pass
