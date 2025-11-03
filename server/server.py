import socket, threading, json, secrets

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.strategy import create_shared_secret_key, encrypt, gen_keypair

HOST, PORT = "127.0.0.1", 5000
clients = {}
pubkeys = {}
groups = {}

# --- Constantes Criptográficas do Cliente (para compatibilidade DH) ---
P = 0xFFFFFFFEFFFFFC2F
G = 5

# --- Chave Privada do Servidor (Para DH com Clientes) ---
SERVER_PRIV, SERVER_PUB = None, None


# --- Funções de Broadcast e Gerenciamento ---
def broadcast_pubkeys():
    """Envia a lista atualizada de pubkeys e a pubkey do servidor a todos os clientes."""
    if not clients:
        return
    # O servidor também envia sua chave pública para que os clientes possam fazer DH com ele
    data = (
        json.dumps({"type": "PUBKEYS", "pubkeys": pubkeys, "server_pub": SERVER_PUB})
        + "\n"
    )  # <-- CORREÇÃO
    for c in clients.values():
        try:
            c.send(data.encode())
        except:
            pass


def send_info(name, msg_text):
    """Envia uma mensagem de informação do servidor para um cliente específico."""
    if name in clients:
        info_msg = json.dumps({"type": "INFO", "msg": msg_text}) + "\n"  # <-- CORREÇÃO
        try:
            clients[name].send(info_msg.encode())
        except:
            pass


def encrypt_group_key_for_member(group_key: bytes, member_pubkey: int) -> dict:
    """
    Criptografa a chave simétrica do grupo usando o DH individual com o membro.
    O servidor usa sua chave privada para DH.
    """
    # 1. DH: Gera a chave secreta compartilhada entre o Servidor e o Membro
    dh_key = create_shared_secret_key(SERVER_PRIV, member_pubkey, P=P)
    # 2. Criptografa a chave de grupo com a chave secreta DH
    return encrypt(dh_key, group_key)


def distribute_group_key(group_name, member_name):
    """Cria/Distribui a Chave de Grupo criptografada para um membro."""

    # 1. Se o grupo não tem chave, ou precisa de uma nova (giro), gera-se uma nova.
    # Neste modelo simplificado, vamos gerar uma chave por grupo e só regenerar em comandos específicos.
    if group_name not in groups or "group_sym_key" not in groups[group_name]:
        groups[group_name]["group_sym_key"] = secrets.token_bytes(
            32
        )  # Chave simétrica de 32 bytes
        groups[group_name]["group_key_encrypted"] = {}

    group_sym_key = groups[group_name]["group_sym_key"]

    # 2. Criptografa a Chave de Grupo Simétrica para o membro individualmente
    if member_name in pubkeys:
        encrypted_key_pkt = encrypt_group_key_for_member(
            group_sym_key, pubkeys[member_name]
        )

        # 3. Armazena a versão criptografada da chave e envia ao cliente
        groups[group_name]["group_key_encrypted"][member_name] = encrypted_key_pkt

        # Envia a chave criptografada para o cliente
        send_group_key_to_client(member_name, group_name, encrypted_key_pkt)
        return True
    return False


def send_group_key_to_client(member_name, group_name, encrypted_key_pkt):
    """Envia o pacote de chave de grupo para o cliente."""
    msg = {"type": "GROUP_KEY", "group_name": group_name, "key_pkt": encrypted_key_pkt}
    if member_name in clients:
        try:
            # ADICIONE \n AO FINAL DO JSON
            clients[member_name].send((json.dumps(msg) + "\n").encode())  # <-- CORREÇÃO
        except:
            pass


def handle_group_command(msg, sender_name):
    """Processa comandos de criação/adição/remoção de grupos."""
    cmd = msg["cmd"]
    group_name = msg["group_name"]
    target_member = msg.get("target_member")

    if cmd == "CREATE":
        if group_name not in groups:
            groups[group_name] = {"members": [sender_name], "inbox": []}
            # O criador precisa receber a chave inicial
            distribute_group_key(group_name, sender_name)
            send_info(sender_name, f"Grupo '{group_name}' criado com sucesso.")
        else:
            send_info(sender_name, f"Erro: Grupo '{group_name}' já existe.")

    elif cmd == "ADD":
        if (
            group_name in groups
            and target_member in pubkeys
            and target_member not in groups[group_name]["members"]
        ):
            groups[group_name]["members"].append(target_member)
            # Distribui a chave de grupo criptografada para o novo membro
            distribute_group_key(group_name, target_member)
            print(f"[SERVER] {target_member} adicionado ao grupo '{group_name}'.")
            send_info(target_member, f"Você foi adicionado ao grupo '{group_name}'.")
            send_info(
                sender_name, f"{target_member} adicionado ao grupo '{group_name}'."
            )
        else:
            send_info(sender_name, "Erro ao adicionar membro ou grupo inválido.")

    elif cmd == "REMOVE":
        if group_name in groups and target_member in groups[group_name]["members"]:
            groups[group_name]["members"].remove(target_member)
            # Para segurança, o ideal seria 'girar' a chave do grupo aqui.
            print(f"[SERVER] {target_member} removido do grupo '{group_name}'.")
            send_info(target_member, f"Você foi removido do grupo '{group_name}'.")
            send_info(sender_name, f"{target_member} removido do grupo '{group_name}'.")
        else:
            send_info(sender_name, "Erro ao remover membro ou grupo inválido.")


def client_thread(conn, addr):
    name = None
    try:
        # 1. Recebe a chave pública do cliente e armazena
        hello = json.loads(conn.recv(4096).decode())
        name = hello["name"]
        pub = hello["pub"]
        clients[name] = conn
        pubkeys[name] = pub

        print(f"[SERVER] {name} conectado de {addr}")
        print(f"[SERVER] {name} pubkey = {pub}")

        broadcast_pubkeys()

        while True:
            data = conn.recv(8192)
            if not data:
                break
            try:
                msg = json.loads(data.decode())
                data_to_send = (json.dumps(msg) + "\n").encode()
            except json.JSONDecodeError as e:
                print(f"EROR DECODING: {e}")
                continue

            # Comando de Grupo
            if msg["type"] == "GROUP_CMD":
                handle_group_command(msg, name)
                continue

            # Mensagem 1-para-1 ou Grupo
            if msg["type"] == "MSG":
                pkt = msg["pkt"]
                print(f"[SERVER] {msg['from']} -> {msg['to']}")
                print(f"  (mensagem original): {msg.get('plaintext','<não enviado>')}")
                print(f"  (cifra): {pkt['c']}\n")

            dest = msg["to"]

            # Encaminhar mensagem para Grupo
            if dest.startswith("GROUP_"):
                group_name = dest
                if name in groups.get(group_name, {}).get("members", []):
                    # Encaminha a mensagem cifrada para todos os membros
                    for member_name in groups[group_name]["members"]:
                        if member_name != name and member_name in clients:
                            clients[member_name].send(data_to_send)
                else:
                    send_info(name, f"Você não é membro do grupo {group_name}.")

            # Encaminhar mensagem 1-para-1 (ou ALL)
            elif dest in clients:
                clients[dest].send(data_to_send)
            elif dest == "ALL":
                for n, c in clients.items():
                    if n != name:
                        c.send(data_to_send)

    except Exception as e:
        print(f"[SERVER] erro: {e}")

    finally:
        if name in clients:
            del clients[name]
        if name in pubkeys:
            del pubkeys[name]
        if name:
            print(f"[SERVER] {name} saiu")
            broadcast_pubkeys()
        if conn:
            conn.close()


def main():
    global SERVER_PRIV, SERVER_PUB
    priv, pub = gen_keypair(G=G, P=P)
    SERVER_PRIV = priv
    SERVER_PUB = pub
    s = socket.socket()
    s.bind((HOST, PORT))
    s.listen()
    print(f"[SERVER] rodando em {HOST}:{PORT}")
    print(f"[SERVER] Chave Pública: {SERVER_PUB}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_thread, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
