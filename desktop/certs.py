"""
JARVIS – certs.py
Erzeugt bei Bedarf ein selbstsigniertes HTTPS-Zertifikat für den
Handy-Zugriff (10 Jahre gültig, liegt im Datenordner). Ersetzt das frühere
generate_cert.py – passiert jetzt automatisch beim Einschalten.
"""

import datetime
import ipaddress
import os

import config


def ensure() -> tuple[str, str]:
    cert_path, key_path = config.SSL_CERT_FILE, config.SSL_KEY_FILE
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    import server

    print("[Certs] Erzeuge selbstsigniertes Zertifikat...")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "jarvis.local")])
    now = datetime.datetime.now(datetime.timezone.utc)
    alt_names = [x509.DNSName("jarvis.local"), x509.DNSName("localhost")]
    try:
        alt_names.append(x509.IPAddress(ipaddress.ip_address(server.get_lan_ip())))
    except ValueError:
        pass

    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .sign(key, hashes.SHA256())
    )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    return cert_path, key_path
