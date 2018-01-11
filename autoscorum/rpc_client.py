import hashlib
import time
import secp256k1
import websocket
import ast


import _struct
from binascii import unhexlify
from collections import OrderedDict
from steem import Steem


from steem.wallet import Wallet
from steembase.types import Signature
from steembase.account import PrivateKey
from steembase.http_client import HttpClient
from steembase import operations
from steembase.transactions import fmt_time_from_now
from steem.transactionbuilder import TransactionBuilder
from steembase.types import (
               Int16, Uint16, Uint32, Uint64,
               String, Bytes, Array, Set, PointInTime, Bool,
               Optional, Map, Id, JsonObj, StaticVariant)


class RpcClient(object):
    def __init__(self, node, keys=[]):
        self.scorumd = Steem(chain_id=node.get_chain_id(), nodes=[node.addr], keys=keys)
        self.wallet = Wallet(self.scorumd)
        self.node = node
        self._ws = None
        self.keys = keys

    def open_ws(self):
        addr = self.node.addr
        retries = 0
        while retries < 10:
            try:
                self._ws = websocket.create_connection(f'ws://{addr}')
                break
            except ConnectionRefusedError:
                retries += 1
                time.sleep(1)

    def close_ws(self):
        if self._ws:
            self._ws.shutdown()

    def get_dynamic_global_properties(self):
        self._ws.send(HttpClient.json_rpc_body('get_dynamic_global_properties', api='database_api'))
        return ast.literal_eval(self._ws.recv())['result']

    def login(self, username: str, password: str):
        self._ws.send(HttpClient.json_rpc_body('login', username, password, api='login_api'))
        return self._ws.recv()

    def get_api_by_name(self, api_name: str):
        self._ws.send(HttpClient.json_rpc_body('call', 1, 'get_api_by_name', [api_name]))
        return self._ws.recv()

    def get_block(self, num: int):
        self._ws.send(HttpClient.json_rpc_body('get_block', num, api='database_api'))
        return ast.literal_eval(self._ws.recv())['result']

    def get_account(self, name: str):
        self._ws.send(HttpClient.json_rpc_body('get_accounts', [name]))
        return self._ws.recv()

    def create_budget(self, owner, balance, deadline, permlink="",):
        op = operations.CreateBudget(
            **{'budget_owner': owner,
               'content_permlink': permlink,
               'balance': '{:.{prec}f} {asset}'.format(
                   float(balance),
                   prec=self.node.chain_params["scorum_prec"],
                   asset=self.node.chain_params["scorum_symbol"]),
               'deadline': deadline
               }
        )
        tx = TransactionBuilder(None,
                                scorumd_instance=self.scorumd,
                                wallet_instance=self.wallet)
        tx.appendOps(op)

        tx.appendSigner(owner, "active")
        tx.sign()

        self._ws.send(HttpClient.json_rpc_body('call', 3, "broadcast_transaction_synchronous", [tx.json()]))
        return self._ws.recv()
        
    def transfer(self, _from: str, to: str, amount: int, memo=""):
        op = operations.Transfer(
            **{"from": _from,
               "to": to,
               "amount": '{:.{prec}f} {asset}'.format(
                   float(amount),
                   prec=self.node.chain_params["scorum_prec"],
                   asset=self.node.chain_params["scorum_symbol"]
               ),
               "memo": memo
               })

        tx = TransactionBuilder(None,
                                scorumd_instance=self.scorumd,
                                wallet_instance=self.wallet)
        tx.appendOps(op)

        tx.appendSigner(_from, "active")
        tx.sign()

        print(tx.json())

        self._ws.send(HttpClient.json_rpc_body('call', 3, "broadcast_transaction_synchronous", [tx.json()]))
        return self._ws.recv()

    def get_ref_block_params(self):
        props = self.get_dynamic_global_properties()
        ref_block_num = props['head_block_number'] - 3 & 0xFFFF
        ref_block = self.get_block(props['head_block_number'] - 2)
        ref_block_prefix = _struct.unpack_from("<I", unhexlify(ref_block["previous"]), 4)[0]
        return Uint16(ref_block_num), Uint32(ref_block_prefix)

    # def _sign(self, transaction, keys):
    #     sigs = []
    #     chainid = self.node.get_chain_id()
    #     a = unhexlify(chainid)
    #     b = b""
    #     for name, value in transaction.items():
    #         if isinstance(value, str):
    #             b += bytes(value, 'utf-8')
    #         else:
    #             b += bytes(value)
    #     message = a + b
    #     digest = hashlib.sha256(message).digest()
    #     for wif in keys:
    #         p = bytes(PrivateKey(wif))
    #         ndata = secp256k1.ffi.new("const int *ndata")
    #         ndata[0] = 0
    #         while True:
    #             ndata[0] += 1
    #             privkey = secp256k1.PrivateKey(p, raw=True)
    #             sig = secp256k1.ffi.new('secp256k1_ecdsa_recoverable_signature *')
    #             signed = secp256k1.lib.secp256k1_ecdsa_sign_recoverable(
    #                 privkey.ctx,
    #                 sig,
    #                 digest,
    #                 privkey.private_key,
    #                 secp256k1.ffi.NULL,
    #                 ndata
    #             )
    #             assert signed == 1
    #             signature, i = privkey.ecdsa_recoverable_serialize(sig)
    #             if self._is_canonical(signature):
    #                 i += 4  # compressed
    #                 i += 27  # compact
    #                 break
    #
    #         sigstr = _struct.pack("<B", i)
    #         sigstr += signature
    #
    #         sigs.append(Signature(sigstr))
    #     transaction["signatures"] = [str(sig)[1:-1] for sig in sigs]
    #     return transaction
    #
    # def _is_canonical(self, sig):
    #     return (not (sig[0] & 0x80) and
    #             not (sig[0] == 0 and not (sig[1] & 0x80)) and
    #             not (sig[32] & 0x80) and
    #             not (sig[32] == 0 and not (sig[33] & 0x80)))
    #
