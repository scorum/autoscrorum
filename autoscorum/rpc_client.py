import json
import time
import _struct
import websocket
import graphenebase

from autoscorum.utils import fmt_time_from_now
from binascii import unhexlify
from graphenebase import operations
from graphenebase.objects import Operation

from graphenebase.signedtransactions import SignedTransaction

from graphenebase.account import PublicKey
from graphenebase.types import (
    Array,
    Set,
    Signature,
    PointInTime,
    Uint16,
    Uint32,
)


class RpcClient(object):
    def __init__(self, node, keys=[]):
        self.node = node
        self._ws = None
        self.keys = keys
        self.chain_id = self.node.get_chain_id()

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

    @staticmethod
    def json_rpc_body(name, *args, api=None, as_json=True, _id=0, kwargs=None):
        """ Build request body for scorum RPC requests.

        Args:
            name (str): Name of a method we are trying to call. (ie: `get_accounts`)
            args: A list of arguments belonging to the calling method.
            api (None, str): If api is provided (ie: `follow_api`),
             we generate a body that uses `call` method appropriately.
            as_json (bool): Should this function return json as dictionary or string.
            _id (int): This is an arbitrary number that can be used for request/response tracking in multi-threaded
             scenarios.

        Returns:
            (dict,str): If `as_json` is set to `True`, we get json formatted as a string.
            Otherwise, a Python dictionary is returned.
        """
        headers = {"jsonrpc": "2.0", "id": _id}
        if kwargs is not None:
            body_dict = {**headers, "method": "call", "params": [api, name, kwargs]}
        elif api:
            body_dict = {**headers, "method": "call", "params": [api, name, args]}
        else:
            body_dict = {**headers, "method": name, "params": args}
        if as_json:
            return json.dumps(body_dict, ensure_ascii=False).encode('utf8')
        else:
            return body_dict

    def get_dynamic_global_properties(self):
        self._ws.send(self.json_rpc_body('get_dynamic_global_properties', api='database_api'))
        return json.loads(self._ws.recv())['result']

    def login(self, username: str, password: str):
        self._ws.send(self.json_rpc_body('login', username, password, api='login_api'))
        return json.loads(self._ws.recv())['result']

    def get_api_by_name(self, api_name: str):
        self._ws.send(self.json_rpc_body('call', 1, 'get_api_by_name', [api_name]))
        return json.loads(self._ws.recv())['result']

    def list_accounts(self, limit: int=100):
        self._ws.send(self.json_rpc_body('call', 0, 'lookup_accounts', ["", limit]))
        return json.loads(self._ws.recv())['result']

    def get_block(self, num: int, **kwargs):
        def request():
            self._ws.send(self.json_rpc_body('get_block', num, api='database_api'))
        wait = kwargs.get('wait_for_block', False)

        request()
        block = json.loads(self._ws.recv())['result']
        if wait and not block:
            timer = 1
            time_to_wait = kwargs.get('time_to_wait', 10)
            while timer < time_to_wait and not block:
                time.sleep(1)
                timer += 1
                request()
                block = json.loads(self._ws.recv())['result']

        return block

    def get_account(self, name: str):
        self._ws.send(self.json_rpc_body('get_accounts', [name]))
        return json.loads(self._ws.recv())['result'][0]

    def list_proposals(self):
        self._ws.send(self.json_rpc_body("call", 0, 'lookup_proposals', []))
        return json.loads(self._ws.recv())['result']

    # def create_budget(self, owner, balance, deadline, permlink="", ):
    #     op = operations.CreateBudget(
    #         **{'owner': owner,
    #            'content_permlink': permlink,
    #            'balance': '{:.{prec}f} {asset}'.format(
    #                float(balance),
    #                prec=self.node.chain_params["scorum_prec"],
    #                asset=self.node.chain_params["scorum_symbol"]),
    #            'deadline': deadline
    #            }
    #     )
    #     tx = TransactionBuilder(None,
    #                             scorumd_instance=self.scorumd,
    #                             wallet_instance=self.wallet)
    #     tx.appendOps(op)
    #
    #     tx.appendSigner(owner, "active")
    #     tx.sign()
    #
    #     self._ws.send(self.json_rpc_body('call', 3, "broadcast_transaction_synchronous", [tx.json()]))
    #     return json.loads(self._ws.recv())

    def get_ref_block_params(self):
        props = self.get_dynamic_global_properties()
        ref_block_num = props['head_block_number'] - 1 & 0xFFFF
        ref_block = self.get_block(props['head_block_number'])
        ref_block_prefix = _struct.unpack_from("<I", unhexlify(ref_block["previous"]), 4)[0]
        return ref_block_num, ref_block_prefix

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

        ref_block_num, ref_block_prefix = self.get_ref_block_params()
        stx = SignedTransaction(ref_block_num=ref_block_num,
                                ref_block_prefix=ref_block_prefix,
                                expiration=fmt_time_from_now(60),
                                operations=[op])

        stx.sign(self.keys, self.chain_id)

        print(stx.json())

        self._ws.send(self.json_rpc_body('call', 3, "broadcast_transaction_synchronous", [stx.json()]))
        return json.loads(self._ws.recv())

    # def invite_member(self, inviter: str, invitee: str, lifetime_sec: int):
    #     op = operations.ProposalCreate(
    #         **{'creator': inviter,
    #            'data': invitee,
    #            'action': 'invite',
    #            'lifetime_sec': lifetime_sec}
    #     )
    #
    #     tx = TransactionBuilder(None,
    #                             scorumd_instance=self.scorumd,
    #                             wallet_instance=self.wallet)
    #     tx.appendOps(op)
    #
    #     tx.appendSigner(inviter, "active")
    #     tx.sign()
    #
    #     print(tx.json())
    #
    #     self._ws.send(self.json_rpc_body('call', 3, "broadcast_transaction_synchronous", [tx.json()]))
    #     return json.loads(self._ws.recv())

    def create_account(self,
                       creator: str,
                       newname: str,
                       owner_pub_key: str,
                       additional_owner_keys=[],
                       additional_active_keys=[],
                       additional_posting_keys=[],
                       additional_owner_accounts=[],
                       additional_active_accounts=[],
                       additional_posting_accounts=[],
                       **kwargs):

        creation_fee = '{:.{prec}f} {asset}'.format(
                   float(kwargs.get('fee', 0.030)),
                   prec=self.node.chain_params["scorum_prec"],
                   asset=self.node.chain_params["scorum_symbol"]
               )
        owner_pubkey = PublicKey(owner_pub_key, prefix=self.scorumd.chain_params["prefix"])
        active_pubkey = PublicKey(kwargs.get("active_key", owner_pub_key), prefix=self.scorumd.chain_params["prefix"])
        posting_pubkey = PublicKey(kwargs.get('posting_key', owner_pub_key), prefix=self.scorumd.chain_params["prefix"])
        memo_pubkey = PublicKey(kwargs.get('memo_key', owner_pub_key), prefix=self.scorumd.chain_params["prefix"])

        owner = format(owner_pubkey, self.scorumd.chain_params["prefix"])
        active = format(active_pubkey, self.scorumd.chain_params["prefix"])
        posting = format(posting_pubkey, self.scorumd.chain_params["prefix"])
        memo = format(memo_pubkey, self.scorumd.chain_params["prefix"])

        owner_key_authority = [[owner, 1]]
        active_key_authority = [[active, 1]]
        posting_key_authority = [[posting, 1]]
        owner_accounts_authority = []
        active_accounts_authority = []
        posting_accounts_authority = []

        # additional authorities
        for k in additional_owner_keys:
            owner_key_authority.append([k, 1])
        for k in additional_active_keys:
            active_key_authority.append([k, 1])
        for k in additional_posting_keys:
            posting_key_authority.append([k, 1])

        for k in additional_owner_accounts:
            owner_accounts_authority.append([k, 1])
        for k in additional_active_accounts:
            active_accounts_authority.append([k, 1])
        for k in additional_posting_accounts:
            posting_accounts_authority.append([k, 1])

        op = operations.AccountCreate(
            **{'fee': creation_fee,
               'creator': creator,
               'new_account_name': newname,
               'owner': {'account_auths': owner_accounts_authority,
                         'key_auths': [[owner_pub_key, 1]],
                         'weight_threshold': 1},
               'active': {'account_auths': active_accounts_authority,
                          'key_auths': [[kwargs.get('active_pub_key', owner_pub_key), 1]],
                          'weight_threshold': 1},
               'posting': {'account_auths': posting_accounts_authority,
                           'key_auths': [[kwargs.get('posting_pub_key', owner_pub_key), 1]],
                           'weight_threshold': 1},
               'memo_key': memo,
               'json_metadata': kwargs.get('json_metadata', {})}
        )

        ops = [Operation(op)]

        ref_block_num, ref_block_prefix = self.get_ref_block_params()

        stx = graphenebase.signedtransactions.SignedTransaction(ref_block_num=ref_block_num,
                                                                ref_block_prefix=ref_block_prefix,
                                                                expiration=fmt_time_from_now(60),
                                                                operations=ops)

        chain = {
            "chain_id": self.node.get_chain_id(),
            "prefix": "SCR",
            "steem_symbol": "SCR",
            "vests_symbol": "SP",
        }

        stx.sign(self.keys, chain)

        print(stx.json())

        self._ws.send(self.json_rpc_body('call', 3, "broadcast_transaction_synchronous", [stx.json()]))
        return json.loads(self._ws.recv())

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
