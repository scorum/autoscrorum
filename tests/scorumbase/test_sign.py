import hashlib
from binascii import hexlify, unhexlify

from graphenebase.ecdsa import sign_message, verify_message

from graphenebase.account import PublicKey
from graphenebase.types import String

from graphenebase import operations
from graphenebase.signedtransactions import SignedTransaction

def test_sha256_hash():
    text = String("text text text")

    h = hashlib.sha256(bytes(text))

    assert(h.hexdigest() == "95e4b20f5e669fab5fdaa2fc9f691192118f72900f9906f13b1883e2fb57aa43")

    digest = unhexlify("95e4b20f5e669fab5fdaa2fc9f691192118f72900f9906f13b1883e2fb57aa43")

    assert(digest == h.digest())

    assert(digest == b'\x95\xe4\xb2\x0f^f\x9f\xab_\xda\xa2\xfc\x9fi\x11\x92'
                     b'\x11\x8fr\x90\x0f\x99\x06\xf1;\x18\x83\xe2\xfbW\xaaC')


def test_sign_message():
    signature = sign_message("text text text", "5JCvGL2GVVpjDrKzbKWPHEvuwFs5HdEGwr4brp8RQiwrpEFcZNP")

    # assert(hexlify(signature) == b'2075625adc5f0a025fa5125e1f1a6493c2ad9798ec18afb49d4a1d9f741ccac16'
    #                              b'441cb10d240046e5cf3b7f10694b62c608047ec037b2ddaec053bdd1f5107c927')

    k = verify_message("text text text", signature)

    p = PublicKey(hexlify(k).decode('ascii'))

    assert(str(p) == "SCR5bgzuweaHx231escVuPVxgudSyUWdKAH7fKgxZfp3nKSirzFRa")


def test_signed_transaction():
    chain_id = "95e4b20f5e669fab5fdaa2fc9f691192118f72900f9906f13b1883e2fb57aa43"
    op = operations.Transfer(
        **{"from": "alice",
           "to": "bob",
           "amount": '0.001 SCR',
           "memo": "for food"
           })

    tx = SignedTransaction(ref_block_num=11105,
                           ref_block_prefix=4052692508,
                           expiration="2018-01-29T08:37:12",
                           operations=[op])

    tx.sign(["5JCvGL2GVVpjDrKzbKWPHEvuwFs5HdEGwr4brp8RQiwrpEFcZNP"], chain_id)

    public_keys = tx.verify(["SCR5bgzuweaHx231escVuPVxgudSyUWdKAH7fKgxZfp3nKSirzFRa"], chain_id)

    assert(len(public_keys) == 1)

    p = PublicKey(public_keys[0])

    assert(str(p) == "SCR5bgzuweaHx231escVuPVxgudSyUWdKAH7fKgxZfp3nKSirzFRa")
