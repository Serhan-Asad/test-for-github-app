"""Extracted from .github/workflows/pdd-secrets-dispatch.yml for testing."""

import os
import json
import base64
import secrets as stdlib_secrets
import requests
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


def encrypt_and_send():
    try:
        # 1. Parse inputs
        secrets_map = json.loads(os.environ.get("SECRETS_CONTEXT", "{}"))
        payload = json.loads(os.environ.get("PAYLOAD_CONTEXT", "{}"))
        public_key_pem = os.environ.get("WORKER_PUBLIC_KEY")

        job_id = payload.get("job_id")
        callback_url = payload.get("callback_url")
        callback_token = payload.get("callback_token")
        required_keys = payload.get("required_secrets", [])

        if not job_id or not callback_url or not callback_token:
            print("::error::Missing job_id, callback_url, or callback_token")
            exit(1)

        # 2. Filter secrets to only those requested
        data_to_encrypt = {}
        if required_keys:
            for key in required_keys:
                if key in secrets_map:
                    data_to_encrypt[key] = secrets_map[key]
        else:
            data_to_encrypt = secrets_map

        if not data_to_encrypt:
            print("No matching secrets found. Sending empty payload.")

        json_data = json.dumps(data_to_encrypt).encode("utf-8")

        # 3. Hybrid encryption: AES-256-GCM for data, RSA-OAEP for AES key
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode("utf-8"),
            backend=default_backend()
        )

        aes_key = stdlib_secrets.token_bytes(32)
        iv = stdlib_secrets.token_bytes(12)

        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(iv, json_data, None)

        encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        envelope = {
            "version": 2,
            "encrypted_key": base64.b64encode(encrypted_key).decode(),
            "iv": base64.b64encode(iv).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
        }

        encrypted_b64 = base64.b64encode(
            json.dumps(envelope).encode()
        ).decode()

        # 4. POST encrypted secrets back to worker
        response = requests.post(
            callback_url,
            json={
                "job_id": job_id,
                "encrypted_secrets": encrypted_b64,
                "callback_token": callback_token,
            },
            timeout=30,
        )

        if response.status_code == 200:
            print(f"Successfully sent secrets for job {job_id}")
        else:
            print(f"::error::Callback failed: {response.status_code} {response.text}")
            exit(1)

    except Exception as e:
        print(f"::error::Script failed: {e}")
        exit(1)


if __name__ == "__main__":
    encrypt_and_send()
