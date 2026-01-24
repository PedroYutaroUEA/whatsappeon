# client/chat_client.py

from pathlib import Path
import socket, threading, json, sys

sys.path.append(str(Path(__file__).parent.parent))


from utils import CryptoService
from .client_manager import ClientManager

# Configurações globais
HOST, PORT = "127.0.0.1", 5000
P = 0xFFFFFFFEFFFFFC2F
G = 5


class ChatClient:
    """Classe principal de I/O de rede (Handler)."""
    def __init__(self, host, port, p, g):
        self.name = input("Seu nome: ")
        self.host = host
        self.port = port
        self.P = p
        self.G = g
        
        # 1. DOMÍNIO: Inicializa Criptografia e Gera Chaves
        crypto_service = CryptoService(P=self.P, G=self.G)
        self.priv, self.pub = crypto_service.gen_keypair()
        
        # 2. REGRA DE NEGÓCIO: Inicializa o Manager com as chaves
        self.manager = ClientManager(self.name, self.priv, self.pub, crypto_service)
        
        self.sock = socket.socket()
        self.RECV_BUFFER = b""

    def run(self):
        self.sock.connect((self.host, self.port))
        
        # DOMÍNIO: Handshake inicial
        handshake_msg = json.dumps({"name": self.name, "pub": self.pub}) + "\n"
        self.sock.send(handshake_msg.encode())
        print(f"[{self.name}] conectado ao servidor")

        threading.Thread(target=self.listener, daemon=True).start()
        self.send_loop()

    def listener(self):
        """Gerencia o recebimento de dados e o buffer de pacotes."""
        # ... (lógica de buffer e enquadramento - JSONDecodeError FIX)
        while True:
            try:
                data = self.sock.recv(8192)
            except Exception as e:
                print(f"ERRO NO SERVER: {e}")
                break
            if not data: break
            self.RECV_BUFFER += data
            while b"\n" in self.RECV_BUFFER:
                line_end_index = self.RECV_BUFFER.find(b"\n")
                package = self.RECV_BUFFER[:line_end_index]
                self.RECV_BUFFER = self.RECV_BUFFER[line_end_index + 1 :]
                if not package: continue
                try:
                    msg = json.loads(package.decode())
                    self._handle_message_receive(msg)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON Decode Error no pacote: {package[:100]}...")
                    continue

        print(f"[{self.name}] Conexão perdida com o servidor.")

    def _handle_message_receive(self, msg):
        """Rotas de recebimento e delegação da Regra de Negócio."""
        
        # Delega ao Manager para atualizar o estado ou decifrar
        if msg["type"] in ["PUBKEYS", "GROUP_KEY"]:
            self.manager.update_state(msg)
        elif msg["type"] == "INFO":
            print(f"\n[SERVER INFO]: {msg['msg']}")
        elif msg["type"] == "MSG":
            self.manager.decrypt_incoming_message(msg) # Delega a decifragem
            
    def send_loop(self):
        """Loop principal de envio de comandos e mensagens (I/O)."""
        while True:
            print("\nComando (MSG, CREATE, ADD, REMOVE, LIST): ")
            action = input().upper()
            
            # Comandos de envio para o Manager
            if action == "MSG":
                dest = input("Destinatário (nome ou GROUP_nome): ")
                text = input("Mensagem: ").encode()
                
                # REGRA DE NEGÓCIO: O Manager decide se pode criar o pacote
                packet, error = self.manager.create_message_packet(dest, text)
                
                if error:
                    print(f"Erro no envio: {error}")
                    continue
                self.sock.send(packet)
            
            # Comandos de Controle (não precisam de lógica complexa, apenas envio)
            elif action in ["CREATE", "ADD", "REMOVE"]:
                group_name = input("Nome do Grupo (ex: GROUP_amigos): ")
                target_member = input("Membro (apenas para ADD/REMOVE; deixe vazio para CREATE): ")

                payload = {
                    "type": "GROUP_CMD",
                    "cmd": action,
                    "group_name": group_name,
                    "target_member": target_member if target_member else None,
                }
                self.sock.send((json.dumps(payload) + "\n").encode())
            
            elif action == "LIST":
                print(f"\nPeers Conhecidos: {list(self.manager.peers_pub.keys())}")
                print(f"Chaves de Grupo Ativas: {list(self.manager.group_sym_keys.keys())}")
            else:
                print("Comando inválido.")