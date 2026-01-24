# server/server_manager.py

import socket
from typing import Dict, List, Any, Optional
import secrets


class ServerManager:
    def __init__(self, P, G, network_utils, crypto):
        self.clients: Dict[str, Any] = {} # {name: conn}
        self.pubkeys: Dict[str, int] = {} # {name: pubkey_int}
        self.groups: Dict[str, Dict[str, Any]] = {} # {group_name: {members: [], group_sym_key: b'', ...}}
        self.P = P
        self.G = G
        self.network = network_utils
        self.crypto = crypto
        
        self.SERVER_PRIV, self.SERVER_PUB = self.crypto.gen_keypair()

    def get_pubkeys_data(self):
        """Retorna o estado das chaves públicas para broadcast, INCLUINDO O TIPO."""
        return {
            "type": "PUBKEYS",
            "pubkeys": self.pubkeys,
            "server_pub": self.SERVER_PUB
        }

    def register_client(self, name: str, pub: int, conn: socket.socket):
        """Adiciona um novo cliente e sua chave pública."""
        self.clients[name] = conn
        self.pubkeys[name] = pub
        print(f"[SERVER] {name} conectado. Pubkey = {pub}")
        # Retorna os dados para broadcast
        return self.get_pubkeys_data()

    def remove_client(self, name: str):
        """Remove o cliente, suas chaves e envia broadcast."""
        if name in self.clients:
            del self.clients[name]
        if name in self.pubkeys:
            del self.pubkeys[name]
        print(f"[SERVER] {name} saiu.")
        return self.get_pubkeys_data()

    # --- Lógica de Gerenciamento de Criptografia ---

    def encrypt_group_key_for_member(self, group_key: bytes, member_pubkey: int) -> dict:
        """Criptografa a chave simétrica do grupo usando DH do Servidor."""
        # Chave secreta compartilhada Servidor-Membro
        dh_key = self.crypto.create_shared_secret_key(self.SERVER_PRIV, member_pubkey)
        # Criptografa a chave do grupo com a chave secreta DH
        return self.crypto.encrypt(dh_key, group_key)

    def distribute_group_key(self, group_name: str, member_name: str) -> bool:
        """Cria e distribui a Chave de Grupo criptografada para um membro."""

        # 1. Se não existe, cria a chave simétrica do grupo
        if group_name not in self.groups or "group_sym_key" not in self.groups[group_name]:
            self.groups[group_name]["group_sym_key"] = secrets.token_bytes(32) # Nova GKS
            print(f"[SERVER] [GKS] NOVA Chave de Grupo Simétrica gerada: {self.groups[group_name]['group_sym_key'].hex()[:12]}...")
            self.groups[group_name]["group_key_encrypted"] = {}

        group_sym_key = self.groups[group_name]["group_sym_key"]

        # 2. Criptografa a GKS para o membro individualmente
        if member_name in self.pubkeys:
            print(f"[SERVER] [EGK] Criptografando GKS para {member_name} (DH com Chave Pública {self.pubkeys[member_name]})...")
            encrypted_key_pkt = self.encrypt_group_key_for_member(
                group_sym_key, self.pubkeys[member_name]
            )

            # 3. Armazena a versão criptografada e envia
            self.groups[group_name]["group_key_encrypted"][member_name] = encrypted_key_pkt

            # Usa o callback de rede para enviar o pacote
            self.network.send_group_key_to_client(member_name, group_name, encrypted_key_pkt)
            return True
        return False

    # --- Lógica de Grupo ---

    def create_group(self, sender_name: str, group_name: str, target_member: Optional[str] = None):
        """
        Cria um grupo e opcionalmente adiciona um membro inicial (além do criador).
        O parâmetro target_member vem do target_member do cliente.
        """
        if group_name not in self.groups:
            self.groups[group_name] = {"members": [sender_name], "inbox": []}
            self.distribute_group_key(group_name, sender_name)
            self.network.send_info(sender_name, f"Grupo '{group_name}' criado com sucesso.")
            if target_member and target_member != sender_name:
                self.add_member_to_group(sender_name, group_name, target_member)
        else:
            self.network.send_info(sender_name, f"Erro: Grupo '{group_name}' já existe.")

    def add_member_to_group(self, sender_name: str, group_name: str, target_member: str):
        if (
            group_name in self.groups
            and target_member in self.pubkeys
            and target_member not in self.groups[group_name]["members"]
        ):
            self.groups[group_name]["members"].append(target_member)
            self.distribute_group_key(group_name, target_member)
            print(f"[SERVER] {target_member} adicionado ao grupo '{group_name}'.")
            self.network.send_info(target_member, f"Você foi adicionado ao grupo '{group_name}'.")
            self.network.send_info(sender_name, f"{target_member} adicionado ao grupo '{group_name}'.")
        else:
            self.network.send_info(sender_name, "Erro ao adicionar membro ou grupo inválido.")

    def remove_member_from_group(self, sender_name: str, group_name: str, target_member: str):
        if group_name in self.groups and target_member in self.groups[group_name]["members"]:
            self.groups[group_name]["members"].remove(target_member)
            # Idealmente, aqui ocorreria o 'giro de chave' (re-keying)
            print(f"[SERVER] {target_member} removido do grupo '{group_name}'.")
            self.network.send_info(target_member, f"Você foi removido do grupo '{group_name}'.")
            self.network.send_info(sender_name, f"{target_member} removido do grupo '{group_name}'.")
        else:
            self.network.send_info(sender_name, "Erro ao remover membro ou grupo inválido.")

    def handle_group_command(self, msg: dict, sender_name: str):
        cmd = msg["cmd"]
        group_name = msg["group_name"]
        target_member = msg.get("target_member")

        if cmd == "CREATE":
            self.create_group(sender_name, group_name)
        elif cmd == "ADD":
            self.add_member_to_group(sender_name, group_name, target_member)
        elif cmd == "REMOVE":
            self.remove_member_from_group(sender_name, group_name, target_member)

    def get_group_members(self, group_name: str) -> List[str]:
        """Retorna a lista de membros do grupo."""
        return self.groups.get(group_name, {}).get("members", [])