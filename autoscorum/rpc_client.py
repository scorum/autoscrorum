import hashlib
import time
import secp256k1

import _struct
from binascii import unhexlify

from steembase.http_client import HttpClient
from steembase.account import PrivateKey
from steembase.types import Signature


class RpcClient(object):
    def __init__(self, nodes, chain_id):
        addrs = []
        for node in nodes:
            addrs.append(node.addr)

        self.chainid = chain_id
        self._keys = {}
        self._rpc = HttpClient(addrs, num_pools=1, retries=1, timeout=1)

    def get_block(self, num):
        result = None
        retry_count = 0
        while retry_count < 10:
            retry_count += 1
            result = self._rpc.exec('get_block', str(num), _ret_cnt=3)
            if result:
                break
            time.sleep(0.2)
        return result

    def set_keys(self, keys):
        self._keys = keys

    def get_account(self, name):
        return self._rpc.exec('get_accounts', [name])[0]

    def get_block_params(self):
        props = self._rpc.exec("get_dynamic_global_properties", api="database_api")
        ref_block_num = props["head_block_number"] - 3 & 0xFFFF
        ref_block = self.exec("get_block", props["head_block_number"] - 2, api="database_api")
        ref_block_prefix = _struct.unpack_from("<I", unhexlify(ref_block["previous"]), 4)[0]
        return ref_block_num, ref_block_prefix

    def get_info(self):
        result = self._rpc.exec("get_dynamic_global_properties", [])

        witness_schedule = self._rpc.exec("get_witness_schedule", [])
        result.update(witness_schedule)

        hardfork_version = self._rpc.exec("get_hardfork_version", [])
        result['hardfork_version'] = hardfork_version

        chain_properties = self._rpc.exec("get_chain_properties", [])
        result.update(chain_properties)

        reward_fund = self._rpc.exec("get_reward_fund", "post")
        result['post_reward_fund'] = reward_fund

        return result

    def _sign(self, wif, transaction):
        sigs = []
        message = unhexlify(self.chainid) + bytes(transaction)
        digest = hashlib.sha256(message).digest()
        for _ in wif:
            p = bytes(PrivateKey(wif))
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
                if self._is_canonical(signature):
                    i += 4  # compressed
                    i += 27  # compact
                    break

            sigstr = _struct.pack("<B", i)
            sigstr += signature

            sigs.append(Signature(sigstr))
        transaction["signatures"] = sigs
        return transaction

    def create_budget(self, owner, balance, deadline, keys=None, broadcast=True, permlink="",):
        ref_block_num, ref_block_prefix = self.get_block_params()
        unsigned_transaction = {"ref_block_num": ref_block_num,
                                "ref_block_prefix": ref_block_prefix,
                                "expiration": "2017-12-27T18:04:27",
                                "operations": [["create_budget", {"owner": owner,
                                                                 "content_permlink": permlink,
                                                                 "balance": balance,
                                                                 "deadline": deadline}]],
                                "extensions": [],
                                "signatures": []}

        self._rpc.exec("broadcast_transaction_synchronous", [[{"ref_block_num": 0,
                                                               "ref_block_prefix": 0,
                                                               "expiration": 0,
                                                               "operations": [["create_budget",
                                                                               {"owner": owner,
                                                                                "content_permlink": permlink,
                                                                                "balance": balance,
                                                                                "deadline:": deadline}]],
                                                               "extensions": [],
                                                               "signatures": []}]])