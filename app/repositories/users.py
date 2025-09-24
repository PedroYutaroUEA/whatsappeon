import json
import os

db_path = os.path.join(os.path.dirname(__file__), "../..", "database", "users.json")


class UserRepository:
    """Model que oferece de recuperações e persistencias em JSON"""

    def write_on_db(self, data):
        with open(db_path, "w", encoding="ut") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def read_on_db(self):
        if not os.path.exists(db_path):
            return {}
            # Abre o arquivo no modo de leitura ('r')
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
