from __future__ import annotations

import argparse
import base64
import binascii
import os
from pathlib import Path


PRIVATE_KEY_HEADERS = (
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
    "-----BEGIN DSA PRIVATE KEY-----",
)
PUBLIC_KEY_PREFIXES = (
    "ssh-ed25519 ",
    "ssh-rsa ",
    "ecdsa-sha2-",
    "sk-ssh-ed25519@openssh.com ",
    "sk-ecdsa-sha2-nistp256@openssh.com ",
)


class SSHKeyFormatError(ValueError):
    pass


def _normalize_text(value: str) -> str:
    text = value.strip().replace("\r\n", "\n").replace("\r", "\n")
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n")
    return text.strip()


def _looks_private_key(value: str) -> bool:
    return value.startswith(PRIVATE_KEY_HEADERS)


def _looks_public_key(value: str) -> bool:
    return value.startswith(PUBLIC_KEY_PREFIXES) or " BEGIN SSH2 PUBLIC KEY " in value


def _decode_base64_candidate(value: str) -> str | None:
    compact = "".join(value.split())
    if compact.lower().startswith("base64:"):
        compact = compact.split(":", 1)[1]
    if not compact:
        return None
    compact += "=" * (-len(compact) % 4)
    try:
        decoded = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError):
        return None
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return _normalize_text(text)


def normalize_private_key_secret(value: str) -> tuple[str, str]:
    raw = _normalize_text(value)
    if not raw:
        raise SSHKeyFormatError("SSH key secret is empty")
    if _looks_private_key(raw):
        return raw + "\n", "raw_private_key"
    if _looks_public_key(raw):
        raise SSHKeyFormatError(
            "SSH key secret contains a public key; store the matching private key instead"
        )

    decoded = _decode_base64_candidate(raw)
    if decoded is not None:
        if _looks_private_key(decoded):
            return decoded + "\n", "base64_private_key"
        if _looks_public_key(decoded):
            raise SSHKeyFormatError(
                "SSH key secret decodes to a public key; store the matching private key instead"
            )

    raise SSHKeyFormatError(
        "SSH key secret is neither a supported private-key block nor base64 of one"
    )


def write_private_key_from_env(*, env_name: str, output: Path) -> str:
    value = os.environ.get(env_name, "")
    normalized, detected_format = normalize_private_key_secret(value)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(normalized, encoding="utf-8")
    output.chmod(0o600)
    return detected_format


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize a private SSH key secret without logging key material."
    )
    parser.add_argument("--env", default="HETZNER_SSH_KEY")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        detected = write_private_key_from_env(env_name=args.env, output=args.output)
    except SSHKeyFormatError as exc:
        print(f"::error::{exc}")
        return 2
    print(f"SSH private-key secret format accepted: {detected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
