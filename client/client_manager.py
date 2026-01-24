# client/client_manager.py
import json
from typing import Dict, Tuple, Optional
from utils import CryptoService

class ClientManager:
    """
    Contém a lógica de Regra de Negócio, o estado do cliente (chaves)
    e a delegação das operações criptográficas.
    """
    
    def __init__(self, name: str, priv: int, pub: int, crypto_service: CryptoService):
        # DOMÍNIO: Dados e Estado
        self.name = name
        self.priv = priv
        self.pub = pub
        self.crypto = crypto_service # Injeção do CryptoStrategy
        self.P = self.crypto.P # Constante P
        
        # DOMÍNIO: Estruturas de Chave
        self.peers_pub: Dict[str, int] = {}
        self.server_pub: Optional[int] = None
        self.group_sym_keys: Dict[str, bytes] = {}
        
    # --- LÓGICA DE ATUALIZAÇÃO DE ESTADO (DOMÍNIO) ---
    
    def update_state(self, msg: dict):
        """Atualiza o estado de chaves baseado em mensagens do servidor (PUBKEYS/GROUP_KEY)."""
        if msg["type"] == "PUBKEYS":
            self.peers_pub = {k: int(v) for k, v in msg["pubkeys"].items() if k != self.name}
            self.server_pub = int(msg["server_pub"])
            print(f"[{self.name}] lista de peers atualizada: {list(self.peers_pub.keys())}")
            print(f"[{self.name}] Chave pública do servidor recebida.")
            return True
        
        if msg["type"] == "GROUP_KEY":
            return self._decrypt_and_store_group_key(msg)
        
        return False

    def _decrypt_and_store_group_key(self, msg: dict) -> bool:
        """REGRA DE NEGÓCIO: Decifra e armazena a Chave de Grupo Simétrica (EGK)."""
        group_name = msg["group_name"]
        key_pkt = msg["key_pkt"]

        if not self.server_pub:
            print(f"Erro: Chave pública do servidor não recebida.")
            return False

        # 1. REGRA DE NEGÓCIO: Calcula a chave secreta compartilhada com o servidor (DH)
        print(f"\n[{self.name}] [DH-EGK] Iniciando destravamento da Chave de Grupo '{group_name}'...")
        dh_key = self.crypto.create_shared_secret_key(self.priv, self.server_pub)

        # 2. REGRA DE NEGÓCIO: Decifra o pacote da Chave de Grupo Simétrica
        ok, group_sym_key = self.crypto.decrypt(dh_key, key_pkt)

        if ok:
            print(f"[{self.name}] [EGK] Chave de Grupo Simétrica (GKS) decifrada: {group_sym_key.hex()[:12]}...")
            self.group_sym_keys[group_name] = group_sym_key
            print(f"[{self.name}] Chave de Grupo '{group_name}' armazenada localmente.")
            return True
        else:
            print(f"\n[{self.name}] Erro ao decifrar a Chave de Grupo '{group_name}'.")
            return False

    # --- LÓGICA DE CRIPTOGRAFIA (REGRA DE NEGÓCIO) ---

    def _get_encryption_key(self, dest: str) -> Optional[bytes]:
        """REGRA DE NEGÓCIO: Determina qual chave de criptografia usar."""
        
        if dest.startswith("GROUP_"):
            return self.group_sym_keys.get(dest)
        
        if dest in self.peers_pub:
            # DH para 1-para-1
            return self.crypto.create_shared_secret_key(self.priv, self.peers_pub[dest])
            
        return None

    def create_message_packet(self, dest: str, text: bytes) -> Tuple[Optional[bytes], Optional[str]]:
        """Criptografa a mensagem e monta o pacote para envio."""
        
        key = self._get_encryption_key(dest)

        if not key:
            return None, f"Chave secreta para {dest} não disponível."

        # DOMÍNIO: Criptografia
        pkt = self.crypto.encrypt(key, text)
        
        # DOMÍNIO: Montagem do pacote de rede
        payload = {
            "type": "MSG",
            "from": self.name,
            "to": dest,
            "pkt": pkt,
            "plaintext": text.decode(),
        }
        return (json.dumps(payload) + "\n").encode(), None
        
    def decrypt_incoming_message(self, msg: dict):
        """Decifra a mensagem recebida e retorna o resultado."""
        sender = msg["from"]
        dest = msg["to"]
        
        # REGRA DE NEGÓCIO: Determina qual chave usar para decifrar
        key = None
        if dest.startswith("GROUP_"):
            key = self.group_sym_keys.get(dest)
        elif sender in self.peers_pub:
            # Mensagem 1-para-1
            key = self.crypto.create_shared_secret_key(self.priv, self.peers_pub[sender])

        if not key:
            print(f"\n[{self.name}] ERRO: Chave para decifrar mensagem de {sender} para {dest} não disponível.")
            return

        # DOMÍNIO: Descriptografia
        ok, plain = self.crypto.decrypt(key, msg["pkt"])
        
        if ok:
            print(f"\n[{sender}] em [{dest}] recebeu: {plain.decode()}")
        else:
            print(f"\n[{sender}] Erro de autenticação (TAG) na mensagem.")