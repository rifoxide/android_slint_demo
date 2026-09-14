#!/usr/bin/env python3
"""Minimal APK Signature Scheme v2 signer (single signer, RSA PKCS1v1.5 SHA-256).
Usage: sign_apk_v2.py <in.apk> <out.apk> <key.pem> <cert.der> <pub.der>
"""
import hashlib
import struct
import subprocess
import sys

SIG_ALGO_ID = 0x0103  # RSASSA-PKCS1-v1_5 with SHA2-256
PAIR_ID_V2 = 0x7109871A
CHUNK = 1048576
MAGIC = b"APK Sig Block 42"


def lp(data: bytes) -> bytes:
    return struct.pack("<I", len(data)) + data


def chunk_digests(section: bytes) -> list[bytes]:
    # AOSP ApkSigningBlockUtils.computeOneMbChunkContentDigests:
    # chunk digest = SHA256(0xa5 || uint32le(chunk_len) || chunk)
    out = []
    for i in range(0, len(section), CHUNK):
        c = section[i : i + CHUNK]
        out.append(hashlib.sha256(b"\xa5" + struct.pack("<I", len(c)) + c).digest())
    return out


def main() -> None:
    in_apk, out_apk, key_pem, cert_der, pub_der = sys.argv[1:6]
    cert = open(cert_der, "rb").read()
    pubkey = open(pub_der, "rb").read()
    apk = open(in_apk, "rb").read()

    eocd_off = apk.rfind(b"PK\x05\x06")
    assert eocd_off != -1, "no EOCD"
    cd_off = struct.unpack_from("<I", apk, eocd_off + 16)[0]
    assert apk[cd_off : cd_off + 4] == b"PK\x01\x02", "bad central directory offset"

    # AOSP canonicalizes the EOCD's central-directory offset to the signing
    # block offset (= original central directory offset) before digesting.
    digest_eocd = bytearray(apk[eocd_off:])
    struct.pack_into("<I", digest_eocd, 16, cd_off)
    chunks = (
        chunk_digests(apk[:cd_off])
        + chunk_digests(apk[cd_off:eocd_off])
        + chunk_digests(bytes(digest_eocd))
    )
    h = hashlib.sha256()
    h.update(b"\x5a")
    h.update(struct.pack("<I", len(chunks)))
    for d in chunks:
        h.update(d)
    digest = h.digest()

    digests = lp(struct.pack("<I", SIG_ALGO_ID) + lp(digest))
    certs = lp(cert)
    signed_data = lp(digests) + lp(certs) + lp(b"")
    sig = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", key_pem],
        input=signed_data,
        capture_output=True,
        check=True,
    ).stdout
    signatures = lp(struct.pack("<I", SIG_ALGO_ID) + lp(sig))
    signer = lp(signed_data) + lp(signatures) + lp(pubkey)
    pair_value = lp(lp(signer))
    pair = struct.pack("<Q", 4 + len(pair_value)) + struct.pack("<I", PAIR_ID_V2) + pair_value
    total = len(pair) + 8 + 16
    block = struct.pack("<Q", total) + pair + struct.pack("<Q", total) + MAGIC

    final_eocd = bytearray(apk[eocd_off:])
    struct.pack_into("<I", final_eocd, 16, cd_off + len(block))
    out = apk[:cd_off] + block + apk[cd_off:eocd_off] + bytes(final_eocd)
    open(out_apk, "wb").write(out)
    print(f"signed {out_apk}: {len(out)} bytes (sig {len(sig)}B, block {len(block)}B)")


if __name__ == "__main__":
    main()
