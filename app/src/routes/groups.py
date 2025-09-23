from flask import Blueprint, jsonify, request

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


@groups_bp.route("/create", methods=["POST"])
def register_group():
    """Rota para registrar usuários."""
    pass


@groups_bp.route("/<groupname>/messages", methods=["POST", "GET"])
def group_messaging_handler():
    """Rota para gerar relatórios de issues."""
    sender = request.headers.get("X-User-Id")
    if not sender:
        return jsonify({"error": "Acesso negado. X-User-Id não encontrado no header"})

    if request.method == "POST":
        # user_controller.send_message()
        pass
    elif request.method == "GET":
        # user_controller.query_message()
        pass
