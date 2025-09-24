from .xor_cipher import XorCipher
from .three_des_cipher import ThreeDESCipher

KEY_SIZE_BYTES = 24


class Strategies:
    """
    Agregador de ciphers
    """

    def __init__(self):
        self.message = ThreeDESCipher()
        self.keys = ThreeDESCipher()

    def generate_key_pair(self):
        return "GERAÇÃO DE CHAVES, ELE MESMO"
