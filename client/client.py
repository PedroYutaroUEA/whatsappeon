import socket, threading, json

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.strategy import decrypt, encrypt, gen_keypair, create_shared_secret_key


HOST, PORT = "127.0.0.1", 5000
P = 0xFFFFFFFEFFFFFC2F
G = 5


# --- Variáveis Globais de Estado ---
name = input("Seu nome: ")
priv, pub = gen_keypair(P, G)
sock = socket.socket()
sock.connect((HOST, PORT))
sock.send(
    (json.dumps({"name": name, "pub": pub}) + "\n").encode()
)  # <-- CORREÇÃOprint(f"[{name}] conectado ao servidor")
RECV_BUFFER = b""

peers_pub = {}
server_pub = None
group_sym_keys = {}  # {group_name: Chave Simétrica Decifrada}


def listener():
    global peers_pub, server_pub, group_sym_keys, RECV_BUFFER
    while True:
        try:
            data = sock.recv(8192)
        except Exception as e:
            print("ERRO NO SERVER: {e}")
            break

        if not data:
            break

        RECV_BUFFER += data

        while b"\n" in RECV_BUFFER:

            line_end_index = RECV_BUFFER.find(b"\n")

            # Extrai o pacote (a linha, sem o \n)
            package = RECV_BUFFER[:line_end_index]

            # Remove o pacote processado e o delimitador do buffer
            RECV_BUFFER = RECV_BUFFER[line_end_index + 1 :]

            # Processa o pacote se não estiver vazio
            if not package:
                continue

            try:
                # Tenta decodificar e carregar o JSON (agora que sabemos que é um pacote completo)
                msg = json.loads(package.decode())
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON Decode Error no pacote: {package[:100]}...")
                continue  # Pula o pacote corrompido

            if msg["type"] == "PUBKEYS":
                peers_pub = {k: int(v) for k, v in msg["pubkeys"].items() if k != name}
                server_pub = int(msg["server_pub"])
                print(f"[{name}] lista de peers atualizada: {list(peers_pub.keys())}")
                print(f"[{name}] Chave pública do servidor recebida.")
                continue

            # --- NOVO: RECEBIMENTO DE CHAVE DE GRUPO ---
            if msg["type"] == "GROUP_KEY":
                group_name = msg["group_name"]
                key_pkt = msg["key_pkt"]

                # 1. Calcula a chave secreta compartilhada com o servidor (DH)
                dh_key = create_shared_secret_key(priv, server_pub, P)

                # 2. Decifra o pacote da Chave de Grupo Simétrica
                ok, group_sym_key = decrypt(dh_key, key_pkt)

                if ok:
                    group_sym_keys[group_name] = group_sym_key
                    print(
                        f"\n[{name}] Chave de Grupo '{group_name}' recebida e decifrada com sucesso!"
                    )
                else:
                    print(
                        f"\n[{name}] Erro ao decifrar a Chave de Grupo '{group_name}'."
                    )
                continue

            # Recebimento de Info
            if msg["type"] == "INFO":
                print(f"\n[SERVER INFO]: {msg['msg']}")
                continue

            # Mensagem recebida
            if msg["type"] == "MSG":
                sender = msg["from"]
                dest = msg["to"]

                key = None
                if dest.startswith("GROUP_"):
                    # Mensagem de Grupo: usa a chave simétrica do grupo
                    group_name = dest
                    key = group_sym_keys.get(group_name)
                    if not key:
                        print(
                            f"\n[{name}] Não é possível decifrar: Chave do grupo '{group_name}' não disponível."
                        )
                        continue

                elif dest in [name] or dest == "ALL":
                    # Mensagem 1-para-1 ou ALL: usa a chave DH com o remetente
                    if sender not in peers_pub:
                        print(
                            f"\n[{name}] Não é possível decifrar: Chave pública de {sender} desconhecida."
                        )
                        continue
                    key = create_shared_secret_key(priv, peers_pub[sender], P)

                if key:
                    ok, plain = decrypt(key, msg["pkt"])
                    if ok:
                        print(f"\n[{sender}] em [{dest}] recebeu: {plain.decode()}")
                    else:
                        print(f"\n[{sender}] Erro de autenticação (TAG) na mensagem.")
    print(f"[{name}] Conexão perdida com o servidor.")


threading.Thread(target=listener, daemon=True).start()

# loop de envio
while True:
    print("\nComando (MSG, CREATE, ADD, REMOVE, LIST): ")
    action = input().upper()

    if action == "MSG":
        dest = input("Destinatário (nome, ALL, ou GROUP_nome): ")
        text = input("Mensagem: ").encode()

        # 1. Envio de Mensagem de Grupo
        if dest.startswith("GROUP_"):
            group_name = dest
            if group_name not in group_sym_keys:
                print(
                    f"Erro: Chave simétrica para '{group_name}' não disponível. Crie/junte-se ao grupo primeiro."
                )
                continue

            # Criptografa UMA VEZ com a Chave Simétrica do Grupo
            key = group_sym_keys[group_name]
            pkt = encrypt(key, text)

            # Envia a mensagem criptografada ao servidor para encaminhamento
            data_to_send = (
                json.dumps(
                    {
                        "type": "MSG",
                        "from": name,
                        "to": dest,
                        "pkt": pkt,
                        "plaintext": text.decode(),
                    }
                )
                + "\n"
            )  # <-- CORREÇÃO

            sock.send(data_to_send.encode())

        # 2. Envio de Mensagem 1-para-1 (ou ALL)
        else:
            targets = [dest] if dest != "ALL" else peers_pub.keys()

            for peer in targets:
                if peer not in peers_pub:
                    print(f"Destinatário '{peer}' desconhecido ou offline. Pulando.")
                    continue

                # Criptografa usando a chave DH individual
                key = create_shared_secret_key(priv, peers_pub[peer], P)
                pkt = encrypt(key, text)

                data_to_send = (
                    json.dumps(
                        {
                            "type": "MSG",
                            "from": name,
                            "to": dest,
                            "pkt": pkt,
                            "plaintext": text.decode(),
                        }
                    )
                    + "\n"
                )  # <-- CORREÇÃO

            sock.send(data_to_send.encode())

    elif action in ["CREATE", "ADD", "REMOVE"]:
        group_name = input("Nome do Grupo (ex: GROUP_amigos): ")
        target_member = input(
            "Membro (apenas para ADD/REMOVE; deixe vazio para CREATE): "
        )

        # Envia o comando de grupo para o servidor
        data_to_send = (
            json.dumps(
                {
                    "type": "GROUP_CMD",
                    "cmd": action,
                    "group_name": group_name,
                    "target_member": target_member if target_member else None,
                }
            )
            + "\n"
        )  # <-- CORREÇÃO

        sock.send(data_to_send.encode())

    elif action == "LIST":
        print(f"\nPeers Conhecidos: {list(peers_pub.keys())}")
        print(f"Chaves de Grupo Ativas: {list(group_sym_keys.keys())}")

    else:
        print("Comando inválido.")
