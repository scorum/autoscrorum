import _struct
import json
import time
from binascii import unhexlify

import autoscorum.operations_fabric as operations
from graphenebase.amount import Amount
from graphenebase.signedtransactions import SignedTransaction
from .account import Account
from .rpc_client import RpcClient
from .utils import fmt_time_from_now


class Wallet(object):
    def __init__(self, chain_id, rpc_endpoint, accounts=[]):
        self.chain_id = chain_id
        self.accounts = accounts
        self.endpoint = rpc_endpoint

        self.rpc = RpcClient()

    def __enter__(self):
        self.rpc.open_ws(self.endpoint)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rpc.close_ws()

    def add_account(self, account):
        acc = account if type(account) is Account else Account(account)
        self.accounts.append(acc)

    def account(self, name: str):
        for account in self.accounts:
            if account.name == name:
                return account
        return None

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
        response = self.rpc.send(self.json_rpc_body('get_dynamic_global_properties', api='database_api'))
        try:
            return response['result']
        except KeyError:
            return response

    def get_circulating_capital(self):
        return Amount(self.get_dynamic_global_properties()['circulating_capital'])

    def login(self, username: str, password: str):
        response = self.rpc.send(self.json_rpc_body('login', username, password, api='login_api'))
        try:
            return response['result']
        except KeyError:
            return response

    def get_api_by_name(self, api_name: str):
        response = self.rpc.send(self.json_rpc_body('call', 'login_api', 'get_api_by_name', [api_name]))
        try:
            return response['result']
        except KeyError:
            return response

    def list_accounts(self, limit: int=100):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'lookup_accounts', ["", limit]))
        try:
            return response['result']
        except KeyError:
            return response

    def list_buddget_owners(self, limit: int=100):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'lookup_budget_owners', ["", limit]))
        try:
            return response['result']
        except KeyError:
            return response

    def list_witnesses(self, limit: int=100):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'lookup_witness_accounts', ["", limit]))
        try:
            return response['result']
        except KeyError:
            return response

    def get_account_history(self, name: str, _from=4294967295, limit=100):
        response = self.rpc.send(self.json_rpc_body('call',
                                                    'account_history_api',
                                                    'get_account_history', [name, _from, limit]))
        try:
            return response['result']
        except KeyError:
            return response

    def get_block(self, num: int, **kwargs):
        def request():
            return self.rpc.send(self.json_rpc_body('get_block', num, api='blockchain_history_api'))
        wait = kwargs.get('wait_for_block', False)

        response = request()
        try:
            block = response['result']
        except KeyError:
            return response
        if wait and not block:
            timer = 1
            time_to_wait = kwargs.get('time_to_wait', 10)*10
            while timer < time_to_wait and not block:
                time.sleep(0.1)
                timer += 1
                block = request()['result']
        return block

    def get_account(self, name: str):
        response = self.rpc.send(self.json_rpc_body('get_accounts', [name]))
        try:
            return response['result'][0]
        except KeyError:
            return response

    def get_account_scr_balance(self, name: str):
        return Amount(self.get_account(name)['balance'])

    def get_account_sp_balance(self, name: str):
        return Amount(self.get_account(name)['scorumpower'])

    def get_account_keys_auths(self, name: str):
        result = {}
        account = self.get_account(name)
        result['owner'] = account['owner']['key_auths'][0][0]
        result['posting'] = account['posting']['key_auths'][0][0]
        result['active'] = account['active']['key_auths'][0][0]
        result['memo'] = account['memo_key']
        return result

    def get_budgets(self, owner_name: str):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'get_budgets', [[owner_name]]))
        try:
            return response['result']
        except KeyError:
            return response

    def get_witness(self, name: str):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'get_witness_by_account', [name]))
        try:
            return response['result']
        except KeyError:
            return response

    def list_proposals(self):
        response = self.rpc.send(self.json_rpc_body("call", 'database_api', 'lookup_proposals', []))
        try:
            return response['result']
        except KeyError:
            return response

    def get_account_by_key(self, pub_key: str):
        response = self.rpc.send(self.json_rpc_body("call", 'account_by_key_api', 'get_key_references', [[pub_key]]))
        try:
            return response['result']
        except KeyError:
            return response

    def get_ref_block_params(self):
        props = self.get_dynamic_global_properties()
        ref_block_num = props['head_block_number'] - 1 & 0xFFFF
        ref_block = self.get_block(props['head_block_number'])
        ref_block_prefix = _struct.unpack_from("<I", unhexlify(ref_block["previous"]), 4)[0]
        return ref_block_num, ref_block_prefix

    def create_budget(self, owner, balance: Amount, deadline, permlink="", ):
        op = operations.create_budget_operation(owner, permlink, balance, deadline)

        signing_key = self.account(owner).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def delegate_scorumpower(self, delegator, delegatee, scorumpower: Amount):
        op = operations.delegate_scorumpower(delegator, delegatee, scorumpower)

        signing_key = self.account(delegator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def transfer(self, _from: str, to: str, amount: Amount, memo=""):
        op = operations.transfer_operation(_from, to, amount, memo)

        signing_key = self.account(_from).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def transfer_to_scorumpower(self, _from: str, to: str, amount: Amount):
        op = operations.transfer_to_scorumpower_operation(_from, to, amount)
        signing_key = self.account(_from).get_active_private()

        return self.broadcast_transaction_synchronous([op], [signing_key])

    def vote_for_witness(self, account: str, witness: str, approve: bool):
        op = operations.AccountWitnessVote(
            **{'account': account,
               'witness': witness,
               'approve': approve}
        )

        signing_key = self.account(account).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def update_witness(self, owner, signing_key, url='testurl.scorum.com', props=None):
        if not props:
            props = {'account_creation_fee': '0.0000000025 SCR',
                     'maximum_block_size': 131072}
        op = operations.witness_update_operation(owner, url, signing_key, props)
        return self.broadcast_transaction_synchronous([op])

    def invite_member(self, inviter: str, invitee: str, lifetime_sec: int):
        op = operations.invite_new_committee_member(inviter, invitee, lifetime_sec)

        signing_key = self.account(inviter).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def vote(self, voter, author, permlink, weight=100):
        op = operations.vote_operation(voter, author, permlink, weight)

        signing_key = self.account(voter).get_posting_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def post_comment(self, author, permlink, parent_author, parent_permlink, title, body, json_metadata):

        op = operations.post_comment_operation(author,
                                               permlink,
                                               parent_author,
                                               parent_permlink,
                                               title, body,
                                               json_metadata)

        signing_key = self.account(author).get_posting_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def get_content(self, author, permlink):
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_content', [author, permlink]))
        try:
            return response['result']
        except KeyError:
            return response

    def get_comments(self, parent_author, parent_permlink, depth):
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_comments', [parent_author, parent_permlink, str(depth)]))
        try:
            return response['result']
        except KeyError:
            return response

    def get_trending_tags(self, start_tag='', limit=100):
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_trending_tags', [start_tag, limit]))
        try:
            return response['result']
        except KeyError:
            return response

    def get_discussions_by(self, by_what, **kwargs):
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_discussions_by_{}'.format(by_what), [kwargs]))
        try:
            return response['result']
        except KeyError:
            return response

    def create_account(self,
                       creator: str,
                       newname: str,
                       owner: str,
                       active: str=None,
                       posting: str=None,
                       fee: Amount=None,
                       memo=None,
                       json_meta={},
                       additional_owner_keys=[],
                       additional_active_keys=[],
                       additional_posting_keys=[],
                       additional_owner_accounts=[],
                       additional_active_accounts=[],
                       additional_posting_accounts=[]):

        op = operations.account_create_operation(creator,
                                                 fee if fee else Amount('0.000000750 SCR'),
                                                 newname,
                                                 owner,
                                                 active if active else owner,
                                                 posting if posting else owner,
                                                 memo if memo else owner,
                                                 json_meta,
                                                 additional_owner_accounts,
                                                 additional_active_accounts,
                                                 additional_posting_accounts,
                                                 additional_owner_keys,
                                                 additional_active_keys,
                                                 additional_posting_keys)

        signing_key = self.account(creator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def create_account_by_committee(self,
                                    creator: str,
                                    newname: str,
                                    owner: str,
                                    active: str=None,
                                    posting: str=None,
                                    memo=None,
                                    json_meta={},
                                    additional_owner_keys=[],
                                    additional_active_keys=[],
                                    additional_posting_keys=[],
                                    additional_owner_accounts=[],
                                    additional_active_accounts=[],
                                    additional_posting_accounts=[]):

        op = operations.account_create_by_committee_operation(creator,
                                                              newname,
                                                              owner,
                                                              active if active else owner,
                                                              posting if posting else owner,
                                                              memo if memo else owner,
                                                              json_meta,
                                                              additional_owner_accounts,
                                                              additional_active_accounts,
                                                              additional_posting_accounts,
                                                              additional_owner_keys,
                                                              additional_active_keys,
                                                              additional_posting_keys)

        signing_key = self.account(creator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def broadcast_transaction_synchronous(self, ops, keys=[]):
        ref_block_num, ref_block_prefix = self.get_ref_block_params()

        tx = SignedTransaction(ref_block_num=ref_block_num,
                               ref_block_prefix=ref_block_prefix,
                               expiration=fmt_time_from_now(60),
                               operations=ops)

        tx.sign(keys, self.chain_id)
        response = self.rpc.send(self.json_rpc_body('call', 'network_broadcast_api', "broadcast_transaction_synchronous", [tx.json()]))

        try:
            return response['result']
        except KeyError:
            return response
