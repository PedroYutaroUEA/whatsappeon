import socket
from typing import Any
from .client_handler import ClientHandler

class ChatServer:
    """Classe principal do servidor, responsável pela escuta e injeção de dependências."""
    
    def __init__(self, host: str, port: int, manager: Any, network_utils: Any):
        self.host = host
        self.port = port
        self.manager = manager # Injeção do ServerManager
        self.network_utils = network_utils # Injeção de callbacks de I/O
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))

    def start(self):
        self.server_socket.listen()
        print(f"[SERVER] rodando em {self.host}:{self.port}")
        print(f"[SERVER] Chave Pública do servidor: {self.manager.SERVER_PUB}")
        
        while True:
            conn, addr = self.server_socket.accept()
            
            # Injeção de Dependência no ClientHandler
            handler = ClientHandler(
                conn, 
                addr, 
                manager=self.manager, 
                network_utils=self.network_utils
            )
            handler.start()