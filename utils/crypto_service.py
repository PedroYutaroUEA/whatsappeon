import secrets, hashlib, hmac

# Constantes Criptográficas (podem ser globais ou passadas para o servidor)
P = 0xFFFFFFFEFFFFFC2F
G = 5


class CryptoService:
    """Encapsula todas as funções de criptografia e DH."""

    def __init__(self, P, G):
        self.P = P
        self.G = G

    def int_to_bytes(self, x: int) -> bytes:
        return x.to_bytes((x.bit_length() + 7) // 8, "big")

    def sha256(self, b: bytes) -> bytes:
        return hashlib.sha256(b).digest()

    def gen_keypair(self) -> tuple[int, int]:
        """Gera um par de chaves DH (privada, pública)."""
        priv = secrets.randbelow(self.P - 2) + 2
        pub = pow(self.G, priv, self.P)
        print(f"[CRYPTO] Chave PRIVADA gerada (DH): {priv}...") # Printar só o valor se for pequeno
        return priv, pub

    def create_shared_secret_key(self, priv: int, pub_peer: int) -> bytes:
        """Calcula a chave secreta compartilhada DH (KS)."""
        ks_bytes = self.sha256(self.int_to_bytes(pow(pub_peer, priv, self.P)))
        print(f"[CRYPTO] Chave Secreta Compartilhada (KS) gerada: {ks_bytes.hex()[:12]}...")
        return ks_bytes

    def keystream(self, key: bytes, nonce: bytes, n: int) -> bytes:
        """Gera a keystream (usada para criptografia XOR/HMAC)."""
        out = b""
        ctr = 1
        while len(out) < n:
            out += hmac.new(key, nonce + ctr.to_bytes(4, "big"), hashlib.sha256).digest()
            ctr += 1
        return out[:n]

    def xor(self, a: bytes, b: bytes) -> bytes:
        return bytes(x ^ y for x, y in zip(a, b))

    def encrypt(self, key: bytes, msg: bytes) -> dict:
        """Criptografa mensagem usando XOR/HMAC."""
        nonce = secrets.token_bytes(8)
        ks = self.keystream(key, nonce, len(msg))
        c = self.xor(msg, ks)
        tag = hmac.new(key, c, hashlib.sha256).digest()
        print(f"[CRYPTO] -> Cifrando: Chave Simétrica {key.hex()[:12]}...")
        print(f"[CRYPTO] -> Cifra (c): {c.hex()[:12]}..., Tag: {tag.hex()[:6]}...")
        return {"nonce": nonce.hex(), "c": c.hex(), "tag": tag.hex()}

    def decrypt(self, key: bytes, pkt: dict) -> tuple[bool, bytes]:
        """Descriptografa mensagem e verifica a TAG."""
        c = bytes.fromhex(pkt["c"])
        nonce = bytes.fromhex(pkt["nonce"])
        tag = bytes.fromhex(pkt["tag"])
        print(f"[CRYPTO] <- Decifrando: Usando Chave {key.hex()[:12]}...")
        
        # 1. Verificação da Integridade (HMAC)
        if not hmac.compare_digest(tag, hmac.new(key, c, hashlib.sha256).digest()):
            print("[CRYPTO] ** FALHA NA AUTENTICAÇÃO (HMAC TAG INVÁLIDA)! **")
            return False, b""
            
        # 2. Descriptografia (XOR)
        ks = self.keystream(key, nonce, len(c))
        print("[CRYPTO] <- Decifragem concluída com sucesso (TAG OK).")
        return True, self.xor(c, ks)