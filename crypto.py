import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from os import urandom

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

password = os.environ.get("APP_PASSWORD")


def get_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    return kdf.derive(password.encode())


def encrypt(plaintext: str) -> str:
    salt = urandom(16)
    key = get_key(password, salt)
    iv = urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padded_plaintext = plaintext + (16 - len(plaintext) % 16) * chr(
        16 - len(plaintext) % 16
    )
    ciphertext = encryptor.update(padded_plaintext.encode()) + encryptor.finalize()
    return urlsafe_b64encode(salt + iv + ciphertext).decode()


def decrypt(ciphertext: str) -> str:
    data = urlsafe_b64decode(ciphertext)
    salt = data[:16]
    iv = data[16:32]
    cipherbytes = data[32:]
    key = get_key(password, salt)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded_plaintext = decryptor.update(cipherbytes) + decryptor.finalize()
    pad_len = decrypted_padded_plaintext[-1]

    res = decrypted_padded_plaintext[:-pad_len].decode()
    assert isinstance(res, str)
    assert len(res) > 0
    return res
