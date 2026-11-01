"""Create all four keys for a NEW Lightsail installation; never replace any key."""
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main():
    target = Path(os.environ.get("AUTH_SECRET_DIR", "/run/secrets"))
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(target.iterdir()):
        raise SystemExit("Secret directory is not empty; refusing to overwrite or mix keys")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    values = {
        "jwt.pem": private.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()),
        "recovery.key": os.urandom(32),
        "lostark-credential.key": os.urandom(32),
        "lostark-fingerprint.key": os.urandom(32),
    }
    for name, content in values.items():
        path = target / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        if os.getuid() == 0:
            os.chown(path, 10001, 10001)
    if os.getuid() == 0:
        os.chown(target, 10001, 10001)
    os.chmod(target, 0o700)
    print("Lightsail keys created; values not displayed")


if __name__ == "__main__":
    main()
