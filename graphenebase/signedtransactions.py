import ecdsa
import hashlib
from binascii import hexlify, unhexlify
from collections import OrderedDict

from .account import PublicKey
from .types import (
    Array,
    Set,
    Signature,
    PointInTime,
    Uint16,
    Uint32,
)


from .objects import GrapheneObject, isArgsThisClass
from .operations import Operation
from .chains import known_chains
from .ecdsa import sign_message, verify_message
import logging
log = logging.getLogger(__name__)

try:
    import secp256k1
    USE_SECP256K1 = True
    log.debug("Loaded secp256k1 binding.")
except Exception:
    USE_SECP256K1 = False
    log.debug("To speed up transactions signing install \n"
              "    pip install secp256k1")


class SignedTransaction(GrapheneObject):
    """ Create a signed transaction and offer method to create the
        signature

        :param num refNum: parameter ref_block_num (see ``getBlockParams``)
        :param num refPrefix: parameter ref_block_prefix (see ``getBlockParams``)
        :param str expiration: expiration date
        :param Array operations:  array of operations
    """
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            if "extensions" not in kwargs:
                kwargs["extensions"] = Set([])
            elif not kwargs.get("extensions"):
                kwargs["extensions"] = Set([])
            if "signatures" not in kwargs:
                kwargs["signatures"] = Array([])
            else:
                kwargs["signatures"] = Array([Signature(unhexlify(a)) for a in kwargs["signatures"]])

            if "operations" in kwargs:
                kwargs['operations'] = SignedTransaction.cast_operations_to_array_of_opklass(kwargs['operations'])

            super().__init__(OrderedDict([
                ('ref_block_num', Uint16(kwargs['ref_block_num'])),
                ('ref_block_prefix', Uint32(kwargs['ref_block_prefix'])),
                ('expiration', PointInTime(kwargs['expiration'])),
                ('operations', kwargs['operations']),
                ('extensions', kwargs['extensions']),
                ('signatures', kwargs['signatures']),
            ]))

    @staticmethod
    def cast_operations_to_array_of_opklass(operations):
        if all([not isinstance(a, Operation) for a in operations]):
            result = Array([Operation(a) for a in operations])
        else:
            result = Array(operations)

        return result

    @staticmethod
    def cast_str_public_keys_to_object(public_keys):
        result = []

        for k in public_keys:
            if not isinstance(k, PublicKey):

                if not isinstance(k, str):
                    raise Exception("")

                result.append(PublicKey(k))
            else:
                result.append(k)

        return result

    @property
    def id(self):
        """ The transaction id of this transaction
        """
        # Store signatures temporarily since they are not part of
        # transaction id
        sigs = self.data["signatures"]
        self.data.pop("signatures", None)

        # Generage Hash of the seriliazed version
        h = hashlib.sha256(bytes(self)).digest()

        # recover signatures
        self.data["signatures"] = sigs

        # Return properly truncated tx hash
        return hexlify(h[:20]).decode("ascii")

    def derive_digest(self, chain_id):
        # Do not serialize signatures
        sigs = self.data["signatures"]
        self.data["signatures"] = []

        # Get message to sign
        #   bytes(self) will give the wire formated data according to
        #   GrapheneObject and the data given in __init__()
        self.message = unhexlify(chain_id) + bytes(self)
        self.digest = hashlib.sha256(self.message).digest()

        # restore signatures
        self.data["signatures"] = sigs

    def verify(self, pubkeys=[], chain_id=None):
        if not chain_id:
            raise Exception("Chain needs to be provided!")

        self.derive_digest(chain_id)
        signatures = self.data["signatures"].data
        pubKeysFound = []

        for signature in signatures:
            p = verify_message(
                self.message,
                bytes(signature)
            )
            phex = hexlify(p).decode('ascii')
            pubKeysFound.append(phex)

        pubkeys = SignedTransaction.cast_str_public_keys_to_object(pubkeys)

        for pubkey in pubkeys:
            if not isinstance(pubkey, PublicKey):
                raise Exception("Pubkeys must be array of 'PublicKey'")

            k = pubkey.unCompressed()[2:]
            if k not in pubKeysFound and repr(pubkey) not in pubKeysFound:
                k = PublicKey(PublicKey(k).compressed())
                raise Exception("Signature for %s missing!" % str(k))

        return pubKeysFound

    def sign(self, wifkeys, chain_id=None):
        """ Sign the transaction with the provided private keys.

            :param list wifkeys: Array of wif keys
            :param str chain_id: identifier for the chain

        """
        if len(wifkeys) == 0:
            raise Exception("wifkeys should't be empty!")

        if not chain_id:
            raise Exception("Chain needs to be provided!")

        self.derive_digest(chain_id)

        # Get Unique private keys
        private_keys = []

        [private_keys.append(item) for item in wifkeys if item not in private_keys]

        # Sign the message with every private key given!
        signatures = []
        for wif in private_keys:
            signature = sign_message(self.message, wif)
            signatures.append(Signature(signature))

        self.data["signatures"] = Array(signatures)
        return self
