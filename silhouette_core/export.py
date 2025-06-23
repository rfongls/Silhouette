import os
import zipfile
import argparse
from datetime import datetime
from cryptography.fernet import Fernet

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
    fernet = Fernet(key)
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for item in files:
            if os.path.isdir(item):
                for root, _, filenames in os.walk(item):
                    for filename in filenames:
                        full_path = os.path.join(root, filename)
                        arcname = os.path.relpath(full_path)
                        with open(full_path, 'rb') as f:
                            data = f.read()
                        encrypted = fernet.encrypt(data)
                        enc_path = arcname + ".enc"
                        zipf.writestr(enc_path, encrypted)
            elif os.path.isfile(item):
                with open(item, 'rb') as f:
                    data = f.read()
                encrypted = fernet.encrypt(data)
                arcname = os.path.relpath(item) + ".enc"
                zipf.writestr(arcname, encrypted)

def generate_key(key_path):
    key = Fernet.generate_key()
    with open(key_path, 'wb') as f:
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
    print(f"[✓] Key generated: {key_path}")

    zip_with_encryption(out_path, DEFAULT_FILES, key)
    print(f"[✓] Backup created: {out_path}")

if __name__ == "__main__":
    main()
