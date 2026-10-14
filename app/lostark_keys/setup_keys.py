"""Create dedicated local secret files; never replace any existing file."""
import os
from pathlib import Path
from app.core.config import settings


def main():
    target = Path(settings.secret_dir)
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    names = ('lostark-credential.key', 'lostark-fingerprint.key')
    if any((target / name).exists() for name in names):
        raise SystemExit('Lost Ark secret files already exist; refusing to overwrite')
    for name in names:
        path = target / name
        with path.open('xb') as stream:
            os.chmod(path, 0o600)
            stream.write(os.urandom(32))
        if os.getuid() == 0:
            os.chown(path, 10001, 10001)
    print('Dedicated Lost Ark encryption/HMAC files created; values not displayed')


if __name__ == '__main__':
    main()
