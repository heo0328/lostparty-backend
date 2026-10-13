"""Generate local-only secrets inside the API container; never replace keys."""
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

target = Path(os.environ.get("AUTH_SECRET_DIR", "/run/secrets"))
target.mkdir(parents=True, exist_ok=True, mode=0o700)
if any((target / name).exists() for name in ("jwt.pem", "recovery.key")):
    raise SystemExit("Keys already exist; refusing to overwrite")
private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
values = {"jwt.pem": private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()), "recovery.key": os.urandom(32)}
for name, content in values.items():
    path = target / name
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(content)
    if os.getuid() == 0:
        os.chown(path, 10001, 10001)
if os.getuid() == 0:
    os.chown(target, 10001, 10001)
os.chmod(target, 0o700)
print("Local keys created; values not displayed")
