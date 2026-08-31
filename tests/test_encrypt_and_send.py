"""Tests for the encrypt_and_send function from pdd-secrets-dispatch.yml.

Covers all execution paths: input validation, secret filtering, hybrid
encryption, callback POST, and error handling.
"""

import os
import json
import base64
import sys
from unittest.mock import patch, MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# Add scripts directory to import path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
from encrypt_and_send import encrypt_and_send


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def rsa_key_pair():
    """Generate a 2048-bit RSA key pair for end-to-end encryption tests."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_key, public_key_pem


def decrypt_payload(private_key, encrypted_b64):
    """Decrypt the encrypted_secrets field to recover the original secrets dict."""
    envelope = json.loads(base64.b64decode(encrypted_b64))
    encrypted_aes_key = base64.b64decode(envelope["encrypted_key"])
    iv = base64.b64decode(envelope["iv"])
    ciphertext = base64.b64decode(envelope["ciphertext"])

    aes_key = private_key.decrypt(
        encrypted_aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    plaintext = AESGCM(aes_key).decrypt(iv, ciphertext, None)
    return json.loads(plaintext)


def _build_env(secrets, payload, public_key_pem):
    """Build the environment variable dict expected by encrypt_and_send."""
    return {
        "SECRETS_CONTEXT": json.dumps(secrets),
        "PAYLOAD_CONTEXT": json.dumps(payload),
        "WORKER_PUBLIC_KEY": public_key_pem,
    }


def _valid_payload(**overrides):
    """Return a payload dict with all required fields, plus any overrides."""
    p = {
        "job_id": "test-job-001",
        "callback_url": "https://worker.example.com/callback",
        "callback_token": "tok-abc-123",
    }
    p.update(overrides)
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_normal_execution_sends_all_secrets(rsa_key_pair, capsys):
    """When no required_secrets filter is specified, all secrets are encrypted and sent."""
    private_key, pub_pem = rsa_key_pair
    secrets = {"API_KEY": "secret-abc", "DB_PASS": "secret-xyz"}
    payload = _valid_payload(job_id="job-all")
    env = _build_env(secrets, payload, pub_pem)

    mock_resp = MagicMock(status_code=200)

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post", return_value=mock_resp) as mock_post:
        encrypt_and_send()

    # Verify POST was called with the right body keys
    mock_post.assert_called_once()
    body = mock_post.call_args.kwargs["json"]
    assert body["job_id"] == "job-all"
    assert body["callback_token"] == "tok-abc-123"

    # Decrypt and verify ALL secrets round-trip
    decrypted = decrypt_payload(private_key, body["encrypted_secrets"])
    assert decrypted == secrets

    assert "Successfully sent secrets for job job-all" in capsys.readouterr().out


def test_filtered_execution_sends_only_requested_secrets(rsa_key_pair, capsys):
    """When required_secrets is specified, only matching secrets are included."""
    private_key, pub_pem = rsa_key_pair
    secrets = {"API_KEY": "abc", "DB_PASS": "xyz", "OTHER": "123"}
    payload = _valid_payload(
        job_id="job-filter",
        required_secrets=["API_KEY", "DB_PASS"],
    )
    env = _build_env(secrets, payload, pub_pem)

    mock_resp = MagicMock(status_code=200)

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post", return_value=mock_resp) as mock_post:
        encrypt_and_send()

    body = mock_post.call_args.kwargs["json"]
    decrypted = decrypt_payload(private_key, body["encrypted_secrets"])

    # Only the two requested keys, not OTHER
    assert decrypted == {"API_KEY": "abc", "DB_PASS": "xyz"}
    assert "OTHER" not in decrypted

    assert "Successfully sent secrets for job job-filter" in capsys.readouterr().out


def test_validation_failure_missing_job_id(rsa_key_pair, capsys):
    """Missing job_id should error-print and exit(1) without calling POST."""
    _, pub_pem = rsa_key_pair
    payload = {
        "callback_url": "https://worker.example.com/callback",
        "callback_token": "tok-no-job",
    }
    env = _build_env({"S": "v"}, payload, pub_pem)

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post") as mock_post:
        with pytest.raises(SystemExit) as exc:
            encrypt_and_send()

    assert exc.value.code == 1
    mock_post.assert_not_called()
    assert "::error::Missing job_id, callback_url, or callback_token" in capsys.readouterr().out


def test_validation_failure_missing_callback_url(rsa_key_pair, capsys):
    """Missing callback_url should error-print and exit(1) without calling POST."""
    _, pub_pem = rsa_key_pair
    payload = {
        "job_id": "job-no-url",
        "callback_token": "tok-no-url",
    }
    env = _build_env({"S": "v"}, payload, pub_pem)

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post") as mock_post:
        with pytest.raises(SystemExit) as exc:
            encrypt_and_send()

    assert exc.value.code == 1
    mock_post.assert_not_called()
    assert "::error::Missing job_id, callback_url, or callback_token" in capsys.readouterr().out


def test_validation_failure_missing_callback_token(rsa_key_pair, capsys):
    """Missing callback_token should error-print and exit(1) without calling POST."""
    _, pub_pem = rsa_key_pair
    payload = {
        "job_id": "job-no-tok",
        "callback_url": "https://worker.example.com/callback",
    }
    env = _build_env({"S": "v"}, payload, pub_pem)

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post") as mock_post:
        with pytest.raises(SystemExit) as exc:
            encrypt_and_send()

    assert exc.value.code == 1
    mock_post.assert_not_called()
    assert "::error::Missing job_id, callback_url, or callback_token" in capsys.readouterr().out


def test_empty_secrets_sends_empty_encrypted_payload(rsa_key_pair, capsys):
    """When no secrets match required_secrets, an empty dict is encrypted and still sent."""
    private_key, pub_pem = rsa_key_pair
    secrets = {"API_KEY": "abc"}
    payload = _valid_payload(
        job_id="job-empty",
        required_secrets=["NONEXISTENT_KEY"],
    )
    env = _build_env(secrets, payload, pub_pem)

    mock_resp = MagicMock(status_code=200)

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post", return_value=mock_resp) as mock_post:
        encrypt_and_send()

    captured = capsys.readouterr().out
    assert "No matching secrets found. Sending empty payload." in captured

    # POST should still be called even with empty secrets
    mock_post.assert_called_once()
    body = mock_post.call_args.kwargs["json"]
    decrypted = decrypt_payload(private_key, body["encrypted_secrets"])
    assert decrypted == {}


def test_callback_failure_non_200_exits_with_error(rsa_key_pair, capsys):
    """Non-200 callback response should print the status/body and exit(1)."""
    _, pub_pem = rsa_key_pair
    payload = _valid_payload(job_id="job-cb-fail")
    env = _build_env({"S": "v"}, payload, pub_pem)

    mock_resp = MagicMock(status_code=500, text="Internal Server Error")

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post", return_value=mock_resp):
        with pytest.raises(SystemExit) as exc:
            encrypt_and_send()

    assert exc.value.code == 1
    assert "::error::Callback failed: 500 Internal Server Error" in capsys.readouterr().out


def test_exception_during_encryption_produces_error(capsys):
    """Invalid WORKER_PUBLIC_KEY should trigger the exception handler and exit(1)."""
    payload = _valid_payload(job_id="job-bad-key")
    env = {
        "SECRETS_CONTEXT": json.dumps({"S": "v"}),
        "PAYLOAD_CONTEXT": json.dumps(payload),
        "WORKER_PUBLIC_KEY": "INVALID_KEY_DATA",
    }

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post") as mock_post:
        with pytest.raises(SystemExit) as exc:
            encrypt_and_send()

    assert exc.value.code == 1
    mock_post.assert_not_called()
    assert "::error::Script failed:" in capsys.readouterr().out


def test_encrypted_envelope_structure(rsa_key_pair):
    """The envelope inside encrypted_secrets must have version=2 plus encrypted_key, iv, ciphertext."""
    _, pub_pem = rsa_key_pair
    payload = _valid_payload(job_id="job-envelope")
    env = _build_env({"MY_SECRET": "value"}, payload, pub_pem)

    mock_resp = MagicMock(status_code=200)

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post", return_value=mock_resp) as mock_post:
        encrypt_and_send()

    body = mock_post.call_args.kwargs["json"]
    envelope = json.loads(base64.b64decode(body["encrypted_secrets"]))

    # Verify envelope keys and version
    assert envelope["version"] == 2
    assert set(envelope.keys()) == {"version", "encrypted_key", "iv", "ciphertext"}

    # Each binary field must be non-empty and valid base64
    for field in ("encrypted_key", "iv", "ciphertext"):
        decoded = base64.b64decode(envelope[field])
        assert len(decoded) > 0, f"'{field}' must be non-empty"


def test_post_request_includes_correct_timeout_and_url(rsa_key_pair):
    """requests.post must be called with the exact callback_url, timeout=30, and json body."""
    _, pub_pem = rsa_key_pair
    target_url = "https://worker.example.com/callback/specific-path"
    payload = _valid_payload(
        job_id="job-post-check",
        callback_url=target_url,
        callback_token="tok-post",
    )
    env = _build_env({"S": "v"}, payload, pub_pem)

    mock_resp = MagicMock(status_code=200)

    with patch.dict(os.environ, env, clear=False), \
         patch("encrypt_and_send.requests.post", return_value=mock_resp) as mock_post:
        encrypt_and_send()

    mock_post.assert_called_once()
    call = mock_post.call_args

    # First positional arg is the URL
    assert call.args[0] == target_url

    # timeout=30 keyword arg
    assert call.kwargs["timeout"] == 30

    # json keyword arg contains expected keys
    body = call.kwargs["json"]
    assert body["job_id"] == "job-post-check"
    assert body["callback_token"] == "tok-post"
    assert "encrypted_secrets" in body
