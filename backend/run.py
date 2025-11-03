
import sys
from pathlib import Path
from types import SimpleNamespace

# Configuração de Path e Constantes
sys.path.append(str(Path(__file__).parent.parent))

from backend.network import broadcast_pubkeys, send_group_key_to_client, send_info
from utils import CryptoService
from backend.server_manager import ServerManager 
from backend.chat_server import ChatServer 

HOST, PORT = "127.0.0.1", 5000
P = 0xFFFFFFFEFFFFFC2F
G = 5


def main():
    # 2. Inicializa as dependências básicas
    crypto_strategy = CryptoService(P=P, G=G)

    network_utils = SimpleNamespace(
        # Broadcast não precisa de argumentos no handler
        broadcast_pubkeys=lambda: broadcast_pubkeys(manager),
        
        # send_info e send_group_key precisam dos argumentos de dados (name, msg_text, etc.)
        send_info=lambda name, msg_text: send_info(manager, name, msg_text),
        send_group_key_to_client=lambda member_name, group_name, pkt: send_group_key_to_client(manager, member_name, group_name, pkt)
    )

    # 4. Inicializa o Manager, passando a estratégia de criptografia e os callbacks de I/O
    manager = ServerManager(
        crypto=crypto_strategy, 
        P=P, G=G,
        network_utils=network_utils # Passa o objeto I/O com todas as funções
    )
    
    # 5. Inicializa o ChatServer, injetando o Manager e os Callbacks
    chat_server = ChatServer(HOST, PORT, manager=manager, network_utils=network_utils)
    
    # 6. Inicia o Servidor
    chat_server.start()


if __name__ == "__main__":
    main()