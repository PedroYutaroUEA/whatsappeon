from flask import Blueprint, jsonify, request
from app.controllers import UsersController

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/create", methods=["POST"])
def register_user():
    """Rota para registrar usuários."""
    user_controller = UsersController()
    return user_controller.register_user()


@users_bp.route("/<username>/messages", methods=["POST, GET"])
def direct_messaging_handler(username: str):
    """Rota para gerar relatórios de issues."""
    sender_username = request.headers.get("X-User-Id")
    if not sender_username:
        return (
            jsonify({"error": "Acesso negado. X-User-Id não encontrado no header."}),
            401,
        )

    user_controller = UsersController()

    if request.method == "POST":
        return user_controller.send_message(sender=sender_username, recipient=username)
    elif request.method == "GET":
        return user_controller.query_messages(username=username)
