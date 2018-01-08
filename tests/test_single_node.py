import time

import pytest
import unittest

from autoscorum.node import Node
from autoscorum.genesis import Genesis
from autoscorum.rpc_client import RpcClient
from steem import Steem

acc_name = "initdelegate"
acc_public_key = "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
acc_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


@pytest.mark.timeout(20, method='signal')
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

        self.wallet = Steem(chain_id=self.node.get_chain_id(),
                            nodes=[self.node.addr],
                            keys=[acc_private_key])

    def tearDown(self):
        self.node.stop()
        print(self.node.logs)

    def test_block_production(self):
        block = self.wallet.get_block(1)

        assert block['witness'] == self.node.config['witness'][1:-1]

    def test_genesis_block(self):
        initdelegate = self.wallet.get_account("initdelegate")
        alice = self.wallet.get_account("alice")
        info = self.wallet.get_dynamic_global_properties()

        assert info['total_supply'] == '1210100.000 SCR'
        assert initdelegate['balance'] == '110000.000 SCR'
        assert alice['balance'] == '100000.000 SCR'

    def test_transfer(self):
        time.sleep(10)
        # login = self.wallet.login(username="", password="")
        # self.wallet.get_api_by_name("database_api")
        # self.wallet.get_api_by_name("network_broadcast_api")
        alice = self.wallet.get_account('alice')
        print(self.wallet.get_account(acc_name))
        self.wallet.commit.transfer(to='alice', amount=10000, asset='SCR', account=acc_name)
        alice = self.wallet.get_account('alice')


























