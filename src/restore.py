import zipfile
import argparse
import os
from cryptography.fernet import Fernet

def decrypt_and_extract(zip_path, key_path, output_dir="restored"):
    with open(key_path, 'rb') as f:
        key = f.read()
    fernet = Fernet(key)

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for name in zipf.namelist():
            if name.endswith(".enc"):
                decrypted_name = name[:-4]
                data = fernet.decrypt(zipf.read(name))
                out_path = os.path.join(output_dir, decrypted_name)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, 'wb') as f:
                    f.write(data)
                print(f"[+] Restored: {decrypted_name}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', required=True, help='Encrypted ZIP file path')
    parser.add_argument('--key', required=True, help='Encryption key file path')
    args = parser.parse_args()

    decrypt_and_extract(args.zip, args.key)

if __name__ == "__main__":
    main()
