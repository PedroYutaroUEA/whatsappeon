from flask import jsonify, request
from app.src.repositories import UserRepository


class UsersController:
    """Controller de usuários"""

    def __init__(self):
        self.users_repo = UserRepository()

    def send_message(self, recipient: str):
        # --- LÓGICA PARA ENVIAR MENSAGEM ---
        sender_username = request.headers.get("X-User-Id")
        if not sender_username:
            return (
                jsonify(
                    {"error": "Acesso negado. X-User-Id não encontrado no header."}
                ),
                401,
            )

        data = request.get_json()
        encrypted_session_key = data.get("encrypted_session_key")
        encrypted_message = data.get("encrypted_message")

        message_data = {
            "from": sender_username,
            "encrypted_session_key": encrypted_session_key,
            "encrypted_message": encrypted_message,
        }

        users_data = self.users_repo.read_on_db()

        if "inbox" not in users_data[recipient]:
            users_data[recipient]["inbox"] = []
        users_data[recipient]["inbox"].append(message_data)

        self.users_repo.write_on_db(users_data)

        print(f"[BACKEND] Mensagem de '{sender_username}' enviada para '{recipient}'.")
        return jsonify({"message": "Mensagem enviada com sucesso."}), 200
