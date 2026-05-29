"""PKI utilities: CA generation, cert signing, WireGuard key generation."""
import os
import base64
import datetime
import logging

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

logger = logging.getLogger(__name__)


def generate_wg_keypair() -> tuple[str, str]:
    """Return (privkey_b64, pubkey_b64) as WireGuard-compatible base64 strings."""
    priv = X25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    pub_bytes = priv.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return base64.b64encode(priv_bytes).decode(), base64.b64encode(pub_bytes).decode()


def _rsa_key(bits: int = 2048):
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def _key_pem(key) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()


def _cert_pem(cert) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def generate_ca(common_name: str = "MeshVPN CA") -> tuple[str, str]:
    """Return (ca_key_pem, ca_cert_pem)."""
    key = _rsa_key(4096)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return _key_pem(key), _cert_pem(cert)


def sign_server_cert(
    ca_key_pem: str,
    ca_cert_pem: str,
    common_name: str,
) -> tuple[str, str]:
    """Generate a server key + cert signed by CA. Return (key_pem, cert_pem)."""
    ca_key = serialization.load_pem_private_key(ca_key_pem.encode(), password=None)
    ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())

    key = _rsa_key(2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=1095))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return _key_pem(key), _cert_pem(cert)


def sign_client_cert(
    ca_key_pem: str,
    ca_cert_pem: str,
    common_name: str,
) -> tuple[str, str]:
    """Generate a client key + cert signed by CA. Return (key_pem, cert_pem)."""
    ca_key = serialization.load_pem_private_key(ca_key_pem.encode(), password=None)
    ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())

    key = _rsa_key(2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=1095))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return _key_pem(key), _cert_pem(cert)


def generate_ta_key() -> str:
    """Generate an OpenVPN static TLS auth key (2048 bits)."""
    raw = os.urandom(256)
    hex_str = raw.hex()
    lines = [hex_str[i : i + 32] for i in range(0, len(hex_str), 32)]
    return (
        "-----BEGIN OpenVPN Static key V1-----\n"
        + "\n".join(lines)
        + "\n-----END OpenVPN Static key V1-----\n"
    )


def generate_dh_params() -> str:
    """
    Generate 2048-bit DH parameters. This can take 20–60 s on first run.
    The result is cached to disk by the caller.
    """
    from cryptography.hazmat.primitives.asymmetric import dh
    logger.info("Generating DH parameters (2048-bit) — this may take a minute…")
    params = dh.generate_parameters(generator=2, key_size=2048)
    return params.parameter_bytes(
        serialization.Encoding.PEM,
        serialization.ParameterFormat.PKCS3,
    ).decode()
