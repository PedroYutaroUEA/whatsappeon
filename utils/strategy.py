import secrets, hashlib, hmac


def int_to_bytes(x):
    return x.to_bytes((x.bit_length() + 7) // 8, "big")


def sha256(b):
    return hashlib.sha256(b).digest()


def create_shared_secret_key(priv, pub_peer, P):
    """Calcula a chave secreta compartilhada DH."""
    return sha256(int_to_bytes(pow(pub_peer, priv, P)))


def keystream(key, nonce, n):
    """Gera a keystream (usada para criptografia XOR/HMAC)."""
    out = b""
    ctr = 1
    while len(out) < n:
        out += hmac.new(key, nonce + ctr.to_bytes(4, "big"), hashlib.sha256).digest()
        ctr += 1
    return out[:n]


def encrypt(key, msg: bytes):
    nonce = secrets.token_bytes(8)
    ks = keystream(key, nonce, len(msg))
    c = xor(msg, ks)
    tag = hmac.new(key, c, hashlib.sha256).digest()
    return {"nonce": nonce.hex(), "c": c.hex(), "tag": tag.hex()}


def decrypt(key, pkt):
    c = bytes.fromhex(pkt["c"])
    nonce = bytes.fromhex(pkt["nonce"])
    tag = bytes.fromhex(pkt["tag"])
    if not hmac.compare_digest(tag, hmac.new(key, c, hashlib.sha256).digest()):
        return False, b""
    ks = keystream(key, nonce, len(c))
    return True, xor(c, ks)


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def gen_keypair(P, G):
    priv = secrets.randbelow(P - 2) + 2
    pub = pow(G, priv, P)
    return priv, pub
