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

        retries = 0
        while retries < 10:
            try:
                self._ws = websocket.create_connection("ws://{addr}".format(addr=self.node.addr))
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

    def list_witnesses(self, limit: int=100):
        self._ws.send(self.json_rpc_body('call', 0, 'lookup_witness_accounts', ["", limit]))
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

    def get_witness(self, name: str):
        self._ws.send(self.json_rpc_body('call', 0, 'get_witness_by_account', [name]))
        return json.loads(self._ws.recv())['result']

    def list_proposals(self):
        self._ws.send(self.json_rpc_body("call", 0, 'lookup_proposals', []))
        return json.loads(self._ws.recv())['result']

    def get_ref_block_params(self):
        props = self.get_dynamic_global_properties()
        ref_block_num = props['head_block_number'] - 1 & 0xFFFF
        ref_block = self.get_block(props['head_block_number'])
        ref_block_prefix = _struct.unpack_from("<I", unhexlify(ref_block["previous"]), 4)[0]
        return ref_block_num, ref_block_prefix

    def create_budget(self, owner, balance, deadline, permlink="", ):
        op = operations.CreateBudget(
            **{'owner': owner,
               'content_permlink': permlink,
               'balance': '{:.{prec}f} {asset}'.format(
                   float(balance),
                   prec=self.node.chain_params["scorum_prec"],
                   asset=self.node.chain_params["scorum_symbol"]),
               'deadline': deadline
               }
        )

        return self.broadcast_transaction_synchronous([op])

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

        return self.broadcast_transaction_synchronous([op])

    def transfer_to_vesting(self, _from: str, to: str, amount: int):
        op = operations.TransferToVesting(
            **{'from': _from,
               'to': to,
               'amount': '{:.{prec}f} {asset}'.format(
                   float(amount),
                   prec=self.node.chain_params["scorum_prec"],
                   asset=self.node.chain_params["scorum_symbol"]
               )
               })

        return self.broadcast_transaction_synchronous([op])

    def vote_for_witness(self, account: str, witness: str, approve: bool):
        op = operations.AccountWitnessVote(
            **{'account': account,
               'witness': witness,
               'approve': approve}
        )

        return self.broadcast_transaction_synchronous([op])

    def invite_member(self, inviter: str, invitee: str, lifetime_sec: int):
        op = operations.ProposalCreate(
            **{'creator': inviter,
               'data': invitee,
               'action': 'invite',
               'lifetime_sec': lifetime_sec}
        )

        return self.broadcast_transaction_synchronous([op])

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
                   asset=self.node.chain_params["scorum_symbol"])

        owner_pubkey = PublicKey(owner_pub_key)
        active_pubkey = PublicKey(kwargs.get("active_key", owner_pub_key))
        posting_pubkey = PublicKey(kwargs.get('posting_key', owner_pub_key))
        memo_pubkey = PublicKey(kwargs.get('memo_key', owner_pub_key))

        owner_key_authority = [[str(owner_pubkey), 1]]
        active_key_authority = [[str(active_pubkey), 1]]
        posting_key_authority = [[str(posting_pubkey), 1]]
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
               'memo_key': str(memo_pubkey),
               'json_metadata': kwargs.get('json_metadata', {})}
        )

        return self.broadcast_transaction_synchronous([op])

    def broadcast_transaction_synchronous(self, ops):
        ref_block_num, ref_block_prefix = self.get_ref_block_params()

        tx = SignedTransaction(ref_block_num=ref_block_num,
                               ref_block_prefix=ref_block_prefix,
                               expiration=fmt_time_from_now(60),
                               operations=ops)

        tx.sign(self.keys, self.chain_id)

        print(tx.json())

        self._ws.send(self.json_rpc_body('call', 3, "broadcast_transaction_synchronous", [tx.json()]))
        return json.loads(self._ws.recv())
