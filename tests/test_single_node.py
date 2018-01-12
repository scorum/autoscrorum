import time

import pytest
import unittest

from autoscorum.node import Node
from autoscorum.genesis import Genesis
from autoscorum.rpc_client import RpcClient
from steembase.transactions import fmt_time_from_now

acc_name = "initdelegate"
acc_public_key = "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
acc_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


# @pytest.mark.timeout(20, method='signal')
class TestSingleNode(unittest.TestCase):
    def setUp(self):
        self.genesis = Genesis()
        self.genesis["init_rewards_supply"] = "1000000.000 SCR"
        self.genesis["init_accounts_supply"] = "210000.000 SCR"
        self.genesis.add_account(acc_name=acc_name,
                                 public_key=acc_public_key,
                                 scr_amount="110000.000 SCR",
                                 witness=True)

        self.genesis.add_account(acc_name='alice',
                                 public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                                 scr_amount="100000.000 SCR")

        self.node = Node(genesis=self.genesis)
        self.node.config['witness'] = f'"{acc_name}"'
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

    def tearDown(self):
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

        assert info['total_supply'] == '1210100.000 SCR'
        assert initdelegate['balance'] == '110000.000 SCR'
        assert alice['balance'] == '100000.000 SCR'

    def test_transfer(self):
        amount = 10000

        initdelegate_balance_before = float(self.rpc.get_account('initdelegate')['balance'].split()[0])
        alice_balance_before = float(self.rpc.get_account('alice')['balance'].split()[0])

        self.rpc.transfer('initdelegate', 'alice', amount)

        initdelegate_balance_after = float(self.rpc.get_account('initdelegate')['balance'].split()[0])
        alice_balance_after = float(self.rpc.get_account('alice')['balance'].split()[0])

        assert initdelegate_balance_after == initdelegate_balance_before - amount
        assert alice_balance_after == alice_balance_before + amount


    def test_create_budget(self):
        print(self.rpc.create_budget('initdelegate', 10000, fmt_time_from_now(3600)))

        print(self.rpc.get_account('initdelegate')['balance'])

























