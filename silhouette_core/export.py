import os
import zipfile
import argparse
from datetime import datetime
try:
    from cryptography.fernet import Fernet
    HAVE_CRYPTO = True
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    HAVE_CRYPTO = False

EXPORT_DIR = "exports"
DEFAULT_FILES = [
    "logs",
    "modules",
    "knowledge_store",
    "logs/memory.jsonl",
    "auto_dev.yaml",
    "PROJECT_MANIFEST.json"
]

def zip_with_encryption(zip_path, files, key):
    """Zip and optionally encrypt a list of files."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for item in files:
            if os.path.isdir(item):
                for root, _, filenames in os.walk(item):
                    for filename in filenames:
                        full_path = os.path.join(root, filename)
                        arcname = os.path.relpath(full_path)
                        with open(full_path, "rb") as f:
                            data = f.read()
                        if HAVE_CRYPTO:
                            data = Fernet(key).encrypt(data)
                            arcname += ".enc"
                        zipf.writestr(arcname, data)
            elif os.path.isfile(item):
                with open(item, "rb") as f:
                    data = f.read()
                arcname = os.path.relpath(item)
                if HAVE_CRYPTO:
                    data = Fernet(key).encrypt(data)
                    arcname += ".enc"
                zipf.writestr(arcname, data)

def generate_key(key_path):
    """Generate an encryption key if possible, otherwise random bytes."""
    if HAVE_CRYPTO:
        key = Fernet.generate_key()
    else:
        key = os.urandom(32)
    with open(key_path, "wb") as f:
        f.write(key)
    return key

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default=None, help='Output zip file path')
    parser.add_argument('--key', type=str, help='Encryption key file path')
    args = parser.parse_args()

    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = args.output or os.path.join(EXPORT_DIR, f"silhouette_backup_{timestamp}.zip")
    key_path = args.key or os.path.join(EXPORT_DIR, f"key_{timestamp}.key")

    key = generate_key(key_path)
    # Use ASCII-only output for compatibility with Windows consoles
    print(f"[OK] Key generated: {key_path}")

    if not HAVE_CRYPTO:
        print("[!] 'cryptography' not installed - archive will not be encrypted")

    zip_with_encryption(out_path, DEFAULT_FILES, key)
    print(f"[OK] Backup created: {out_path}")
    print("Backup complete")

if __name__ == "__main__":
    main()
