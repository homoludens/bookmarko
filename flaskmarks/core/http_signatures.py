"""HTTP Signatures for ActivityPub (draft-cavage-http-signatures).

Provides signing of outgoing requests and verification of incoming
signatures using RSA-SHA256.
"""
from __future__ import annotations

import base64
import hashlib
import time
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend


def sign_headers(
    private_key_pem: str,
    key_id: str,
    method: str,
    path: str,
    host: str,
) -> dict[str, str]:
    """Create HTTP Signature headers for an outgoing request.

    Args:
        private_key_pem: PEM-encoded RSA private key.
        key_id: The public key ID URL (actor_id#main-key).
        method: HTTP method (GET, POST, etc.).
        path: Request path (/inbox, etc.).
        host: Target host.

    Returns:
        Dict of headers to add to the request.
    """
    date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

    # Build the signing string
    signing_string = (
        f'(request-target): {method.lower()} {path}\n'
        f'host: {host}\n'
        f'date: {date}'
    )

    # Load private key
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None,
        backend=default_backend(),
    )

    # Sign
    signature = private_key.sign(
        signing_string.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature_b64 = base64.b64encode(signature).decode('utf-8')

    # Build Signature header
    signature_header = (
        f'keyId="{key_id}",'
        f'algorithm="rsa-sha256",'
        f'headers="(request-target) host date",'
        f'signature="{signature_b64}"'
    )

    return {
        'Date': date,
        'Signature': signature_header,
    }


def verify_signature(
    public_key_pem: str,
    method: str,
    path: str,
    host: str,
    date: str,
    signature_b64: str,
) -> bool:
    """Verify an HTTP Signature on an incoming request.

    Args:
        public_key_pem: PEM-encoded RSA public key of the sender.
        method: HTTP method used.
        path: Request path.
        host: Request host header.
        date: Date header value.
        signature_b64: Base64-encoded signature from the Signature header.

    Returns:
        True if signature is valid, False otherwise.
    """
    signing_string = (
        f'(request-target): {method.lower()} {path}\n'
        f'host: {host}\n'
        f'date: {date}'
    )

    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend(),
        )

        signature = base64.b64decode(signature_b64)

        public_key.verify(
            signature,
            signing_string.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False