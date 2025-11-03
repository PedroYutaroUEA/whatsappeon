from .server_manager import ServerManager
import json

# --- 1. Funções de Rede (I/O) - Fora das Classes ---
def broadcast_pubkeys(manager: ServerManager):
    """Envia a lista atualizada de pubkeys e a pubkey do servidor a todos os clientes."""
    data_to_send = json.dumps(manager.get_pubkeys_data()) + "\n"
    encoded_data = data_to_send.encode()
    for c in manager.clients.values():
        try:
            c.send(encoded_data)
        except:
            pass

def send_info(manager: ServerManager, name: str, msg_text: str):
    """Envia uma mensagem de informação do servidor para um cliente específico."""
    if name in manager.clients:
        info_msg = json.dumps({"type": "INFO", "msg": msg_text}) + "\n"
        try:
            manager.clients[name].send(info_msg.encode())
        except:
            pass

def send_group_key_to_client(manager: ServerManager, member_name: str, group_name: str, encrypted_key_pkt: dict):
    """Envia o pacote de chave de grupo para o cliente."""
    msg = {"type": "GROUP_KEY", "group_name": group_name, "key_pkt": encrypted_key_pkt}
    if member_name in manager.clients:
        try:
            manager.clients[member_name].send((json.dumps(msg) + "\n").encode())
        except:
            pass