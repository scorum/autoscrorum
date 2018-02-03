import struct
import secp256k1
import hashlib

import json
from binascii import hexlify, unhexlify

from scorumbase.keys import PrivateKey

from scorumbase.types import (
    Array,
    Set,
    Signature,
    PointInTime,
    Uint16,
    Uint32,
)


def _is_canonical(sig):
    return (not (sig[0] & 0x80) and
            not (sig[0] == 0 and not (sig[1] & 0x80)) and
            not (sig[32] & 0x80) and
            not (sig[32] == 0 and not (sig[33] & 0x80)))


def sign(wifkeys, digest=bytes()):
    # Get Unique private keys
    privkeys = []
    [privkeys.append(item) for item in wifkeys if item not in privkeys]

    # Sign the message with every private key given!
    sigs = []
    for wif in privkeys:
        p = bytes(PrivateKey(wif))
        i = 0
        ndata = secp256k1.ffi.new("const int *ndata")
        ndata[0] = 0
        while True:
            ndata[0] += 1
            privkey = secp256k1.PrivateKey(p, raw=True)
            sig = secp256k1.ffi.new('secp256k1_ecdsa_recoverable_signature *')
            signed = secp256k1.lib.secp256k1_ecdsa_sign_recoverable(
                privkey.ctx,
                sig,
                digest,
                privkey.private_key,
                secp256k1.ffi.NULL,
                ndata
            )
            assert signed == 1
            signature, i = privkey.ecdsa_recoverable_serialize(sig)
            if _is_canonical(signature):
                i += 4   # compressed
                i += 27  # compact
                break

        # pack signature
        sigstr = struct.pack("<B", i)
        sigstr += signature

        sigs.append(Signature(sigstr))

    return sigs


def verify_message(message, signature, hashfn=hashlib.sha256):
    if not isinstance(message, bytes):
        message = bytes(message, "utf-8")
    if not isinstance(signature, bytes):
        signature = bytes(signature, "utf-8")
    assert isinstance(message, bytes)
    assert isinstance(signature, bytes)
    digest = hashfn(message).digest()
    sig = signature[1:]
    recoverParameter = (signature[0]) - 4 - 27  # recover parameter only

    ALL_FLAGS = secp256k1.lib.SECP256K1_CONTEXT_VERIFY | secp256k1.lib.SECP256K1_CONTEXT_SIGN
    # Placeholder
    pub = secp256k1.PublicKey(flags=ALL_FLAGS)
    # Recover raw signature
    sig = pub.ecdsa_recoverable_deserialize(sig, recoverParameter)
    # Recover PublicKey
    verifyPub = secp256k1.PublicKey(pub.ecdsa_recover(message, sig))
    # Convert recoverable sig to normal sig
    normalSig = verifyPub.ecdsa_recoverable_convert(sig)
    # Verify
    verifyPub.ecdsa_verify(message, normalSig)
    phex = verifyPub.serialize(compressed=True)

    return phex