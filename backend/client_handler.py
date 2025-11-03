import threading, json
from typing import Any

class ClientHandler(threading.Thread):
    """Encapsula o thread de comunicação e a lógica de recebimento/encaminhamento."""
    
    def __init__(self, conn, addr, manager: Any, network_utils: Any):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.manager = manager # Injeção do ServerManager
        self.network_utils = network_utils # Injeção de funções de I/O de rede
        self.name = None
        self.RECV_BUFFER = b'' # Buffer local para tratamento de JSON

    def run(self):
        try:
            # 1. DOMÍNIO: Handshake inicial
            hello_data = self.conn.recv(4096).decode()
            hello = json.loads(hello_data)
            self.name = hello["name"]
            pub = hello["pub"]
            
            # REGRA DE NEGÓCIO: Registro de cliente
            self.manager.register_client(self.name, pub, self.conn)
            print(f"[SERVER] {self.name} conectado de {self.addr}")
            self.network_utils.broadcast_pubkeys() # Chama a função injetada
            # self.server.network_utils.broadcast_pubkeys() # <-- CORREÇÃO: Chama o wrapper injetado

            while True:
                data = self.conn.recv(8192)
                if not data:
                    break
                
                # --- Lógica de Enquadramento (Framing) ---
                self.RECV_BUFFER += data
                
                while b"\n" in self.RECV_BUFFER:
                    line_end_index = self.RECV_BUFFER.find(b"\n")
                    package = self.RECV_BUFFER[:line_end_index]
                    self.RECV_BUFFER = self.RECV_BUFFER[line_end_index + 1 :]
                    
                    if not package: continue
                    
                    try:
                        msg = json.loads(package.decode())
                        data_to_send = (json.dumps(msg) + "\n").encode()
                    except json.JSONDecodeError as e:
                        print(f"[SERVER ERROR] JSON Decode Error from {self.name}: {e}")
                        continue

                    # REGRA DE NEGÓCIO: Processamento de comandos
                    if msg["type"] == "GROUP_CMD":
                        self.manager.handle_group_command(msg, self.name)
                        continue

                    # DOMÍNIO: Encaminhamento de mensagens
                    if msg["type"] == "MSG":
                        self._handle_message_forwarding(msg, data_to_send)

        except Exception as e:
            print(f"[SERVER] erro em {self.name}: {e}")

        finally:
            self._cleanup()

    def _handle_message_forwarding(self, msg, data_to_send):
        """Lógica de encaminhamento de mensagens 1:1 e grupo."""
        dest = msg["to"]
        
        # Pega as estruturas de dados do Manager
        groups = self.manager.groups
        clients = self.manager.clients

        if dest.startswith("GROUP_"):
            group_name = dest
            members = groups.get(group_name, {}).get("members", [])
            
            # REGRA DE NEGÓCIO: Verifica se é membro antes de encaminhar
            if self.name in members:
                print(f"[SERVER] {self.name} -> GRUPO {group_name}")
                # DOMÍNIO: Encaminha para todos os membros
                for member_name in members:
                    if member_name != self.name and member_name in clients:
                        clients[member_name].send(data_to_send)
            else:
                self.network_utils.send_info(self.name, f"Você não é membro do grupo {group_name}.")

        elif dest in clients:
            print(f"[SERVER] {self.name} -> {dest}")
            clients[dest].send(data_to_send)
        else:
             self.network_utils.send_info(self.name, f"Destinatário '{dest}' desconhecido ou offline.")


    def _cleanup(self):
        """Remove o cliente das estruturas globais ao sair."""
        if self.name:
            # O manager lida com a remoção e o broadcast
            self.manager.remove_client(self.name)
        if self.conn:
            self.conn.close()