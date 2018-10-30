import _struct
import json
import time
from binascii import unhexlify

import scorum.graphenebase.operations_fabric as operations
from scorum.graphenebase.amount import Amount
from scorum.graphenebase.signedtransactions import SignedTransaction
from scorum.utils.time import fmt_time_from_now

from automation.account import Account
from automation.rpc_client import RpcClient


class Wallet(object):
    def __init__(self, chain_id, rpc_endpoint, accounts=None):
        self.chain_id = chain_id
        self.accounts = accounts if accounts else []
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
        return response.get('result', response)

    def get_circulating_capital(self):
        return Amount(self.get_dynamic_global_properties()['circulating_capital'])

    def login(self, username: str, password: str):
        response = self.rpc.send(self.json_rpc_body('login', username, password, api='login_api'))
        return response.get('result', response)

    def get_api_by_name(self, api_name: str):
        response = self.rpc.send(self.json_rpc_body('call', 'login_api', 'get_api_by_name', [api_name]))
        return response.get('result', response)

    def list_accounts(self, limit: int = 100, start_name: str = ""):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'lookup_accounts', [start_name, limit]))
        return response.get('result', response)

    def list_all_accounts(self):
        limit = 100
        names = []
        last = ""
        while True:
            accs = self.list_accounts(limit, last)

            if len(names) == 0:
                names += accs
            else:
                names += accs[1:]

            if len(accs) < limit or names[-1] == last:
                break
            last = accs[-1]
        return names

    def list_buddget_owners(self, limit: int = 100, budget_type="post"):
        response = self.rpc.send(self.json_rpc_body(
            'call', 'database_api', 'lookup_budget_owners', [budget_type, "", limit])
        )
        return response.get('result', response)

    def get_config(self):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'get_config', []))
        return response.get('result', response)

    def list_witnesses(self, limit: int = 100):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'lookup_witness_accounts', ["", limit]))
        return response.get('result', response)

    def get_account_history(self, name: str, _from=4294967295, limit=100):
        response = self.rpc.send(self.json_rpc_body(
            'call',
            'account_history_api',
            'get_account_history', [name, _from, limit]
        ))
        return response.get('result', response)

    def get_account_transfers(self, name: str, _from="sp", to="scr", starts=-1, limit=100):
        transfer_types = ["sp", "scr"]
        if _from not in transfer_types and to not in transfer_types or(_from == "sp" and to == "sp"):
            raise ValueError("Supported only next types of transfers: scr-scr, scr-sp, sp-scr.")
        response = self.rpc.send(self.json_rpc_body(
            'call', 'account_history_api',
            'get_account_%s_to_%s_transfers' % (_from, to),
            [name, starts, limit]
        ))
        return response.get('result', response)

    def get_development_committee(self):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'get_development_committee', []))
        return response.get('result', response)

    def get_devcommittee_transfers(self, _from="sp", to="scr", starts=-1, limit=100):
        transfer_types = ["sp", "scr"]
        if _from not in transfer_types or to != "scr":
            raise ValueError("History is allowed only for scr-scr and sp-scr devcommittee transfers.")
        response = self.rpc.send(self.json_rpc_body(
            'call', 'devcommittee_history_api',
            'get_%s_to_%s_transfers' % (_from, to),
            [starts, limit]
        ))
        return response.get('result', response)

    def get_last_block_duration_in_microseconds(self):
        response = self.rpc.send(self.json_rpc_body(
            'call',
            'node_monitoring_api',
            'get_last_block_duration_microseconds', []
        ))
        return response.get('result', response)

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
            time_to_wait = kwargs.get('time_to_wait', num * 3) * 10
            while timer < time_to_wait and not block:
                time.sleep(0.1)
                timer += 1
                block = request()['result']
        return block

    def get_ops_in_block(self, num, operation_type=0):
        """
        Returns sequence of operations included/generated in a specified block

        :param int num: Number of block in chain.
        :param int operation_type: Operations type (all = 0, not_virt = 1, virt = 2, market = 3)
        :rtype: dict
        """
        response = self.rpc.send(self.json_rpc_body(
            'call', 'blockchain_history_api', 'get_ops_in_block', [num, operation_type]
        ))
        return response.get('result', response)

    def get_ops_history(self, from_op=-1, limit=100, op_type=0):
        """
        Returns operations in ids range in descending order.

        :param int from_op: Start operation id, -1 is most recent operation.
        :param int limit: Number of operations to return. Max: 100.
        :param int op_type: Operations type (all = 0, not_virt = 1, virt = 2, market = 3).
        :return list: operations in ids range
        """
        response = self.rpc.send(self.json_rpc_body(
            'call', 'blockchain_history_api', 'get_ops_history', [from_op, limit, op_type]
        ))
        return response.get('result', response)

    def get_accounts(self, names: list):
        response = self.rpc.send(self.json_rpc_body('get_accounts', names))
        return response.get('result', response)

    def get_account(self, name: str):
        return self.get_accounts([name])[0]

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

    def get_budgets(self, owners: list, budget_type="post"):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'get_budgets', [budget_type, owners]))
        return response.get('result', response)

    def get_chain_capital(self):
        response = self.rpc.send(self.json_rpc_body('call', 'chain_api', 'get_chain_capital', [], _id=1))
        return response.get('result', response)

    def get_witness(self, name: str):
        response = self.rpc.send(self.json_rpc_body('call', 'database_api', 'get_witness_by_account', [name]))
        return response.get('result', response)

    def list_proposals(self):
        response = self.rpc.send(self.json_rpc_body("call", 'database_api', 'lookup_proposals', []))
        return response.get('result', response)

    def get_account_by_key(self, pub_key: str):
        response = self.rpc.send(self.json_rpc_body("call", 'account_by_key_api', 'get_key_references', [[pub_key]]))
        return response.get('result', response)

    def get_ref_block_params(self):
        props = self.get_dynamic_global_properties()
        ref_block_num = props['head_block_number'] - 1 & 0xFFFF
        ref_block = self.get_block(props['head_block_number'])
        ref_block_prefix = _struct.unpack_from("<I", unhexlify(ref_block["previous"]), 4)[0]
        return ref_block_num, ref_block_prefix

    def get_budget(self, uuid, budget_type="post"):
        response = self.rpc.send(self.json_rpc_body(
            "call", 'advertising_api', 'get_budget', [uuid, budget_type]
        ))
        return response.get('result', response)

    def get_auction_coefficients(self, budget_type="post"):
        response = self.rpc.send(self.json_rpc_body(
            "call", 'advertising_api', 'get_auction_coefficients', [budget_type]
        ))
        return response.get('result', response)

    def get_moderator(self):
        response = self.rpc.send(self.json_rpc_body("call", 'advertising_api', 'get_moderator', []))
        return response.get('result', response)

    def get_user_budgets(self, account):
        response = self.rpc.send(self.json_rpc_body("call", 'advertising_api', 'get_user_budgets', [account]))
        return response.get('result', response)

    def create_budget(self, uuid, owner, balance, start, deadline, json_metadata="{}", type="post"):
        op = operations.create_budget_operation(uuid, owner, json_metadata, balance, start, deadline, type)
        signing_key = self.account(owner).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def close_budget(self, uuid, owner, type):
        op = operations.close_budget_operation(uuid, owner, type)
        signing_key = self.account(owner).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def close_budget_by_advertising_moderator(self, uuid, moderator: str, type="post"):
        op = operations.close_budget_by_advertising_moderator(uuid, moderator, type)
        signing_key = self.account(moderator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def update_budget(self, uuid, owner, json_metadata, type):
        op = operations.update_budget_operation(uuid, owner, json_metadata, type)
        signing_key = self.account(owner).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def get_current_winners(self, type='post'):
        response = self.rpc.send(self.json_rpc_body('call', 'advertising_api', 'get_current_winners', [type]))
        return response.get('result', response)

    def delegate_scorumpower(self, delegator, delegatee, scorumpower: Amount):
        op = operations.delegate_scorumpower(delegator, delegatee, scorumpower)
        signing_key = self.account(delegator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def transfer(self, _from: str, to: str, amount: Amount, memo=""):
        op = operations.transfer_operation(_from, to, amount, memo)
        signing_key = self.account(_from).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def withdraw(self, account: str, scorumpower: Amount):
        op = operations.withdraw(account, scorumpower)
        signing_key = self.account(account).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def devcommittee_withdraw_vesting(self, account: str, scorumpower: Amount, lifetime=86400):
        op = operations.devpool_withdraw_vesting(account, scorumpower, lifetime)
        signing_key = self.account(account).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def development_committee_empower_advertising_moderator(self, initiator: str, moderator: str, lifetime=86400):
        op = operations.development_committee_empower_advertising_moderator(initiator, moderator, lifetime)
        signing_key = self.account(initiator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def development_committee_empower_betting_moderator(self, initiator: str, moderator: str, lifetime=86400):
        op = operations.development_committee_empower_betting_moderator(initiator, moderator, lifetime)
        signing_key = self.account(initiator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def development_committee_change_betting_resolve_delay(self, initiator, delay_sec, lifetime=86400):
        op = operations.development_committee_change_betting_resolve_delay(initiator, delay_sec, lifetime)
        signing_key = self.account(initiator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def development_committee_change_budgets_auction_properties(
        self, initiator: str, coeffs: list, lifetime=86400, type="post"
    ):
        op = operations.development_committee_change_budgets_auction_properties(
            initiator, lifetime, coeffs, type
        )
        signing_key = self.account(initiator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def transfer_to_scorumpower(self, _from: str, to: str, amount: Amount):
        op = operations.transfer_to_scorumpower_operation(_from, to, amount)
        signing_key = self.account(_from).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def proposal_vote(self, account: str, proposal_id: int):
        op = operations.proposal_vote_operation(account, proposal_id)
        signing_key = self.account(account).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def vote_for_witness(self, account: str, witness: str, approve: bool):
        op = operations.account_witness_vote_operation(
            **{'account': account,
               'witness': witness,
               'approve': approve}
        )
        signing_key = self.account(account).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def update_witness(self, owner, signing_key, url='testurl.scorum.com', props=None):
        if not props:
            props = {'account_creation_fee': '0.0000000025 SCR', 'maximum_block_size': 131072}
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
        op = operations.post_comment_operation(
            author,
            permlink,
            parent_author,
            parent_permlink,
            title, body,
            json_metadata
        )
        signing_key = self.account(author).get_posting_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def get_content(self, author, permlink=""):
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_content', [author, permlink]))
        return response.get('result', response)

    def get_contents(self, content_queries: list):
        """
        :param list(dict) content_queries: List of author/permlink pairs
        :return:
        """
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_contents', [content_queries]))
        return response.get('result', response)

    def get_comments(self, parent_author, parent_permlink, depth):
        response = self.rpc.send(
            self.json_rpc_body('call', 'tags_api', 'get_comments', [parent_author, parent_permlink, str(depth)]))
        return response.get('result', response)

    def get_trending_tags(self, start_tag='', limit=100):
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_trending_tags', [start_tag, limit]))
        return response.get('result', response)

    def get_discussions_by(self, by_what, **kwargs):
        response = self.rpc.send(
            self.json_rpc_body('call', 'tags_api', 'get_discussions_by_{}'.format(by_what), [kwargs]))
        return response.get('result', response)

    def get_paid_posts_comments_by_author(self, **kwargs):
        response = self.rpc.send(
            self.json_rpc_body('call', 'tags_api', 'get_paid_posts_comments_by_author', [kwargs]))
        return response.get('result', response)

    def get_parents(self, **content_query):
        """
        :param dict content_query: author/permlink pair
        :return:
        """
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_parents', [content_query]))
        return response.get('result', response)

    def get_stats_for_interval(self, time_from: str, time_to: str):  # %Y-%m-%dT%H:%M:%S
        response = self.rpc.send(self.json_rpc_body(
            'call', 'blockchain_statistics_api', 'get_stats_for_interval', [time_from, time_to]))
        return response.get('result', response)

    def get_posts_and_comments(self, **discussion_query):
        response = self.rpc.send(self.json_rpc_body('call', 'tags_api', 'get_posts_and_comments', [discussion_query]))
        return response.get('result', response)

    def debug_has_hardfork(self, hardfork_id):
        response = self.rpc.send(self.json_rpc_body('call', 'debug_node_api', 'debug_has_hardfork', [hardfork_id]))
        return response.get('result', response)

    def debug_set_hardfork(self, hardfork_id):
        response = self.rpc.send(self.json_rpc_body('call', 'debug_node_api', 'debug_set_hardfork', [hardfork_id]))
        return response.get('result', response)

    def create_account(self, creator: str, newname: str, owner: str, **kwargs):
        op = operations.account_create_operation(
            creator,
            kwargs.get('fee', Amount('0.000000750 SCR')),
            newname,
            owner,
            kwargs.get('active', owner),
            kwargs.get('posting', owner),
            kwargs.get('memo', owner),
            kwargs.get('json_meta', {}),
            kwargs.get('additional_owner_accounts', []),
            kwargs.get('additional_active_accounts', []),
            kwargs.get('additional_posting_accounts', []),
            kwargs.get('additional_owner_keys', []),
            kwargs.get('additional_active_keys', []),
            kwargs.get('additional_posting_keys', []),
        )
        signing_key = self.account(creator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def create_account_by_committee(self,  creator: str, newname: str, owner: str, **kwargs):
        op = operations.account_create_by_committee_operation(
            creator,
            newname,
            owner,
            kwargs.get('active', owner),
            kwargs.get('posting', owner),
            kwargs.get('memo', owner),
            kwargs.get('json_meta', {}),
            kwargs.get('additional_owner_accounts', []),
            kwargs.get('additional_active_accounts', []),
            kwargs.get('additional_posting_accounts', []),
            kwargs.get('additional_owner_keys', []),
            kwargs.get('additional_active_keys', []),
            kwargs.get('additional_posting_keys', []),
        )
        signing_key = self.account(creator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def broadcast_transaction_synchronous(self, ops, keys=None):
        ref_block_num, ref_block_prefix = self.get_ref_block_params()
        tx = SignedTransaction(
            ref_block_num=ref_block_num,
            ref_block_prefix=ref_block_prefix,
            expiration=fmt_time_from_now(60),
            operations=ops
        )
        tx.sign(keys if keys else [], self.chain_id)
        response = self.rpc.send(
            self.json_rpc_body('call', 'network_broadcast_api', "broadcast_transaction_synchronous", [tx.json()])
        )
        return response.get('result', response)

    def broadcast_multiple_ops(self, op_name: str, data: list, users: set):
        op = getattr(operations, op_name)
        ops = [op(**d) for d in data]
        keys = [self.account(u).get_active_private() for u in users]
        return self.broadcast_transaction_synchronous(ops, keys)

    def get_games_by_status(self, game_filters: list):
        """
        :param int game_filters: Enum(created, started, finished, resolved, expired, cancelled)
            Statuses 'resolved', 'expired', 'cancelled' returns Null as game should be deleted in such cases.
            To retrieve all games send ['created', 'started', 'finished']
        """
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'get_games_by_status', [game_filters]))
        return response.get('result', response)

    def get_games_by_uuids(self, uuids):
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'get_games_by_uuids', [uuids]))
        return response.get('result', response)

    def lookup_games_by_id(self, start_id, limit):
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'lookup_games_by_id', [start_id, limit]))
        return response.get('result', response)

    def get_game_winners(self, game_uuid):
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'get_game_winners', [game_uuid]))
        return response.get('result', response)

    def get_matched_bets(self, uuids):
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'get_matched_bets', [uuids]))
        return response.get('result', response)

    def lookup_matched_bets(self, start_id, limit):
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'lookup_matched_bets', [start_id, limit]))
        return response.get('result', response)

    def get_pending_bets(self, uuids):
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'get_pending_bets', [uuids]))
        return response.get('result', response)

    def lookup_pending_bets(self, start_id, limit):
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'lookup_pending_bets', [start_id, limit]))
        return response.get('result', response)

    def get_betting_properties(self):
        response = self.rpc.send(self.json_rpc_body('call', 'betting_api', 'get_betting_properties', []))
        return response.get('result', response)

    def create_game(self, uuid, moderator, json_metadata, start_time, resolve_delay, game, markets):
        op = operations.create_game(uuid, moderator, json_metadata, start_time, resolve_delay, game, markets)
        signing_key = self.account(moderator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def cancel_game(self, uuid, moderator):
        op = operations.cancel_game(uuid, moderator)
        signing_key = self.account(moderator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def update_game_markets(self, uuid, moderator, markets):
        op = operations.update_game_markets(uuid, moderator, markets)
        signing_key = self.account(moderator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def update_game_start_time(self, uuid, moderator, start_time):
        op = operations.update_game_start_time(uuid, moderator, start_time)
        signing_key = self.account(moderator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def post_game_results(self, uuid, moderator, wincases):
        op = operations.post_game_results(uuid, moderator, wincases)
        signing_key = self.account(moderator).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def post_bet(self, uuid, better, game_uuid, wincase, odds, stake, live):
        op = operations.post_bet(uuid, better, game_uuid, wincase, odds, stake, live)
        signing_key = self.account(better).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])

    def cancel_pending_bets(self, uuids, better):
        op = operations.cancel_pending_bets(uuids, better)
        signing_key = self.account(better).get_active_private()
        return self.broadcast_transaction_synchronous([op], [signing_key])
