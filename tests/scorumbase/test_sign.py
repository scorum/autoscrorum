import hashlib
import json
from scorumbase import ecdsa

from scorumbase.keys import PublicKey
from scorumbase.types import String, Signature
from binascii import hexlify, unhexlify


def test_sha256_hash():
    text = String("text text text")

    h = hashlib.sha256(bytes(text))

    assert(h.hexdigest() == "95e4b20f5e669fab5fdaa2fc9f691192118f72900f9906f13b1883e2fb57aa43")

    digest = unhexlify("95e4b20f5e669fab5fdaa2fc9f691192118f72900f9906f13b1883e2fb57aa43")

    assert(digest == h.digest())

    assert(digest == b'\x95\xe4\xb2\x0f^f\x9f\xab_\xda\xa2\xfc\x9fi\x11\x92'
                     b'\x11\x8fr\x90\x0f\x99\x06\xf1;\x18\x83\xe2\xfbW\xaaC')


def test_sign():

    text = String("text text text")
    h = hashlib.sha256(bytes(text))

    sigs = sign(["5JCvGL2GVVpjDrKzbKWPHEvuwFs5HdEGwr4brp8RQiwrpEFcZNP"], h.digest())

    assert(1 == len(sigs))

    assert(bytes(sigs[0]) == b' K\xf1lv\xd8\x0f\x92\x917G\xf59\xa4\xff\xcb\x85\xeas\x19|\x10\x12'
                             b'\x8b\xc3@X\x0e\t\xb6\t\xb7\xdc{=\xd0\xd0\xa6p\x03D)\xfe\xc1\xb6'
                             b'\xebN\xae4t;\x13]\xcfk(\xba\xad\x07"\xdbg\xc8\x95\xba')

    print(sigs[0])

    print(verify_message("text text text", "204bf16c76d80f92913747f539a4ffcb85ea73197c10128bc340580e09b609b7dc7b3dd0d0a670034429fec1b6eb4eae34743b135dcf6b28baad0722db67c895ba"))
    # assert(str(sigs[0]) == '"204bf16c76d80f92913747f539a4ffcb85ea73197c10128bc340580e09b609b7d'
    #                        'c7b3dd0d0a670034429fec1b6eb4eae34743b135dcf6b28baad0722db67c895ba"')

    # 1f031d7b6115ad416cf33e313dd9fd81f537a912e7fba0f9bca339740d93c6cd9915e58ffd726a0be213cc7ca3f04cb9e6dc245a0f355609cdab1104bb881de6d1
    # 204bf16c76d80f92913747f539a4ffcb85ea73197c10128bc340580e09b609b7dc7b3dd0d0a670034429fec1b6eb4eae34743b135dcf6b28baad0722db67c895ba
    # 200c00672f50721ddad9c9e17476f0a5a2b9445dd4fc13415569d4c808bc5f208008114cfc08ecaaee43abe25939ea83f079d009c17cdc08e93054d199d6fd15bc
#
#     my = MySign()
#
#     digest = hashlib.sha256(unhexlify("5ba96d2f6cbde94018464405519cd2ec16cbe6da4437849a7591a89d15abd494")).digest()
#
#     print(my.sign(["5JCvGL2GVVpjDrKzbKWPHEvuwFs5HdEGwr4brp8RQiwrpEFcZNP"], digest)[0].__str__())

def derSigToHexSig(s):
    """ Format DER to HEX signature
    """
    import ecdsa as ee

    s, junk = ecdsa.der.remove_sequence(unhexlify(s))
    assert (junk == b'')
    x, s = ecdsa.der.remove_integer(s)
    y, s = ecdsa.der.remove_integer(s)
    return '%064x%064x' % (x, y)


def test_signing_text():
    signature = ecdsa.sign_message("text text text", "5JCvGL2GVVpjDrKzbKWPHEvuwFs5HdEGwr4brp8RQiwrpEFcZNP")

    print(hexlify(signature))

    k = ecdsa.verify_message("text text text", signature)

    p = PublicKey(hexlify(k).decode('ascii'))

    print(p)

    # assert(hexlify(k) ==
