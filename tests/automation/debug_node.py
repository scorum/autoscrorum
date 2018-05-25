import pytest

from autoscorum.rpc_client import RpcClient


@pytest.mark.skip(reason="no way of currently testing this")
class MyNode:
    chain_params = {"chain_id": None,
                    "prefix": "SCR",
                    "scorum_symbol": "SCR",
                    "sp_symbol": "SP",
                    "scorum_prec": 9,
                    "sp_prec": 9}

    addr = "127.0.0.1:8090"

    def __init__(self):
        pass

    def get_chain_id(self):
        return "d957c4dc98e5bf2784eb46f3200fef8516555bb23200feb31ea2eeb9481e0393"


class TestsMy:
    def setup_method(self):
        self.node = MyNode()
        self.rpc = RpcClient(self.node, ["5JCvGL2GVVpjDrKzbKWPHEvuwFs5HdEGwr4brp8RQiwrpEFcZNP"])
        self.rpc.open_ws()
        self.rpc.login("", "")
        self.rpc.get_api_by_name('database_api')
        self.rpc.get_api_by_name('network_broadcast_api')
        self.rpc.get_block(1, wait_for_block=True)

    def teardown_method(self):
        pass

    def test_create_account(self):
        test_account_name = 'bob'
        test_account_pub_key = 'SCR7w8tySAVQmJ95xSL8SS2GJJCws9s2gCY85DSAEALMFPmaMKA6p'

        print(self.rpc.create_account('initdelegate', newname=test_account_name, owner_pub_key=test_account_pub_key))

        accounts = self.rpc.list_accounts()

        assert(len(accounts) == 3)

        assert(test_account_name in accounts)
