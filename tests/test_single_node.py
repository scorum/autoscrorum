from autoscorum.node import Node
from autoscorum.genesis import Genesis
from autoscorum.rpc_client import RpcClient
from autoscorum.utils import fmt_time_from_now

acc_name = "initdelegate"
acc_public_key = "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
acc_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


# @pytest.mark.timeout(20, method='signal')
class TestSingleNode:
    def setup_method(self):
        self.genesis = Genesis()
        self.genesis["init_rewards_supply"] = "1000000.000000000 SCR"
        self.genesis["init_accounts_supply"] = "210000.000000000 SCR"
        self.genesis.add_account(acc_name=acc_name,
                                 public_key=acc_public_key,
                                 scr_amount="110000.000000000 SCR",
                                 witness=True)

        self.genesis.add_account(acc_name='alice',
                                 public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                                 scr_amount="100000.000000000 SCR")

        self.node = Node(genesis=self.genesis)
        self.node.config['witness'] = '"{acc_name}"'.format(acc_name=acc_name)
        self.node.config['private-key'] = acc_private_key
        self.node.config['public-api'] = "database_api login_api account_by_key_api"
        self.node.config['enable-plugin'] = 'witness account_history account_by_key'

        self.node.run()

        self.rpc = RpcClient(self.node, [acc_private_key])
        self.rpc.open_ws()
        self.rpc.login("", "")
        self.rpc.get_api_by_name('database_api')
        self.rpc.get_api_by_name('network_broadcast_api')
        self.rpc.get_block(1, wait_for_block=True)

    def teardown_method(self):
        self.rpc.close_ws()
        self.node.stop()
        print(self.node.logs)

    def test_block_production(self):
        block = self.rpc.get_block(1)

        assert block['witness'] == self.node.config['witness'][1:-1]

    def test_genesis_block(self):
        initdelegate = self.rpc.get_account("initdelegate")
        alice = self.rpc.get_account("alice")
        info = self.rpc.get_dynamic_global_properties()

        assert info['total_supply'] == '1210100.000000000 SCR'
        assert initdelegate['balance'] == '110000.000000000 SCR'
        assert alice['balance'] == '100000.000000000 SCR'

    def test_transfer(self):
        initdelegate_balance_before = float(self.rpc.get_account('initdelegate')['balance'].split()[0])
        amount = int(initdelegate_balance_before - 100)
        alice_balance_before = float(self.rpc.get_account('alice')['balance'].split()[0])

        print(self.rpc.transfer('initdelegate', 'alice', amount))

        initdelegate_balance_after = float(self.rpc.get_account('initdelegate')['balance'].split()[0])
        alice_balance_after = float(self.rpc.get_account('alice')['balance'].split()[0])

        assert initdelegate_balance_after == initdelegate_balance_before - amount
        assert alice_balance_after == alice_balance_before + amount

    def test_transfer_invalid_amount(self):
        initdelegate_balance_before = float(self.rpc.get_account('initdelegate')['balance'].split()[0])
        amount = int(initdelegate_balance_before + 1)
        alice_balance_before = float(self.rpc.get_account('alice')['balance'].split()[0])

        response = self.rpc.transfer('initdelegate', 'alice', amount)

        initdelegate_balance_after = float(self.rpc.get_account('initdelegate')['balance'].split()[0])
        alice_balance_after = float(self.rpc.get_account('alice')['balance'].split()[0])

        assert initdelegate_balance_after == initdelegate_balance_before
        assert alice_balance_after == alice_balance_before

        assert 'Account does not have sufficient funds for transfer' in response['error']['message']

    def test_transfer_to_vesting(self):
        initdelegate_scr_balance_before = float(self.rpc.get_account('initdelegate')['balance'].split()[0])
        alice_sp_balance_before = float(self.rpc.get_account('alice')['vesting_shares'].split()[0])

        amount = 1

        self.rpc.transfer_to_vesting('initdelegate', 'alice', amount)

        initdelegate_scr_balance_after = float(self.rpc.get_account('initdelegate')['balance'].split()[0])
        alice_sp_balance_after = float(self.rpc.get_account('alice')['vesting_shares'].split()[0])

        assert initdelegate_scr_balance_after == initdelegate_scr_balance_before - amount
        assert alice_sp_balance_after == alice_sp_balance_before + amount

    def test_create_account(self):
        test_account_name = 'bob'
        test_account_pub_key = 'SCR7w8tySAVQmJ95xSL8SS2GJJCws9s2gCY85DSAEALMFPmaMKA6p'

        self.rpc.create_account('initdelegate', newname=test_account_name, owner=test_account_pub_key)

        accounts = self.rpc.list_accounts()

        assert(len(accounts) == 3)

        assert(test_account_name in accounts)

    # def test_vote_for_witness(self):
    #     self.rpc.transfer_to_vesting('initdelegate', 'alice', 1)
    #     alice_sp = float(self.rpc.get_account('alice')['vesting_shares'].split()[0])
    #
    #     votes_before = self.rpc.get_witness('initdelegate')['votes']
    #
    #     print(self.rpc.vote_for_witness('alice', 'initdelegate', True))
    #
    #     votes_after = self.rpc.get_witness('initdelegate')['votes']
    #
    #     assert votes_after == votes_before + alice_sp

    # def test_create_budget(self):
    #     print(self.rpc.create_budget('initdelegate', 10000, fmt_time_from_now(3600)))
    #
    #     print(self.rpc.get_account('initdelegate')['balance'])
    #
    # def test_invite_member(self):
    #     print(self.rpc.invite_member('initdelegate', 'alice', 86500))
    #
    #     print(self.rpc.list_proposals())
