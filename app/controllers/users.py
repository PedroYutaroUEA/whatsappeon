from flask import jsonify, request
from app.repositories import UserRepository
from app.ciphers import Strategies


class UsersController:
    """Controller de usuários"""

    def __init__(self):
        self.repository = UserRepository()
        self.strategies = Strategies()

    def __user_exists(self, username):
        users = self.repository.read_on_db()
        return username in users

    def register_user(self):
        data = request.get_json()
        username = data.get("username")

        if not username:
            return jsonify({"error": "Nome de usuário é obrigatório."}), 400

        users = self.repository.read_on_db()
        if username in users:
            return jsonify({"error": "Usuário já existe."}), 409

        # 1. GERAÇÃO DAS CHAVES
        private_key, public_key = self.strategies.generate_key_pair()

        users[username] = {"public_key": public_key, "inbox": []}

        self.repository.write_on_db(users)

        print(f"[BACKEND] Usuário '{username}' registrado. Chave pública salva.")

        # ENVIA A CHAVE PRIVADA DE VOLTA PARA O CLIENTE
        # O cliente DEVE armazená-la de forma segura (sim, isso é problema dele, sem mais)
        return (
            jsonify(
                {
                    "message": "Usuário registrado com sucesso. Salve sua chave privada!",
                    "username": username,
                    "private_key": private_key,
                }
            ),
            201,
        )

    def query_messages(self, username: str):
        users = self.repository.read_on_db()

        if not self.__user_exists(username=username):
            return {"error", f"Usuário '{username}' não existe"}, 404

        inbox = users[username].get("inbox", [])

        # Limpa a caixa de entrada no banco de dados e salva a alteração
        users[username]["inbox"] = []
        self.repository.write_on_db(users)

        return inbox, 200

    def send_message(self, sender: str, recipient: str):
        # --- LÓGICA PARA ENVIAR MENSAGEM ---
        data = request.get_json()
        encrypted_session_key = data.get("encrypted_session_key")
        encrypted_message = data.get("encrypted_message")

        message_data = {
            "from": sender,
            "encrypted_session_key": encrypted_session_key,
            "encrypted_message": encrypted_message,
        }

        users = self.repository.read_on_db()

        if "inbox" not in users[recipient]:
            users[recipient]["inbox"] = []
        users[recipient]["inbox"].append(message_data)

        self.repository.write_on_db(users)

        print(f"[BACKEND] Mensagem de '{sender}' enviada para '{recipient}'.")
        return jsonify({"message": "Mensagem enviada com sucesso."}), 200
