import time

from autoscorum.node import Node
from autoscorum.genesis import Genesis
from autoscorum.rpc_client import RpcClient
from steem import Steem

acc_name = "initdelegate"
acc_public_key = "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
acc_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


def test_block_production():
    genesis = Genesis()
    genesis["init_supply"] = 10000
    genesis.add_account(acc_name=acc_name,
                        public_key=acc_public_key,
                        scr_amount=10000,
                        witness=True)

    node = Node(genesis=genesis)
    node.config['witness'] = f'"{acc_name}"'
    node.config['private-key'] = acc_private_key

    node.run()
    scorumd = Steem(chain_id=node.get_chain_id(), nodes=[node.addr])
    block = scorumd.get_block(1)
    node.stop()

    assert block['witness'] == node.config['witness'][1:-1]


def test_genesis_block():
    genesis = Genesis()
    genesis["init_supply"] = 210000
    genesis.add_account(acc_name=acc_name,
                        public_key=acc_public_key,
                        scr_amount=110000,
                        witness=True)
    genesis.add_account(acc_name='alice',
                        public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                        scr_amount=100000)

    node = Node(genesis=genesis)
    node.config['witness'] = f'"{acc_name}"'
    node.config['private-key'] = acc_private_key
    node.run()

    scorumd = Steem(chain_id=node.get_chain_id(), nodes=[node.addr])
    initdelegate = scorumd.get_account("initdelegate")
    alice = scorumd.get_account("alice")
    info = scorumd.get_dynamic_global_properties()
    node.stop()

    assert info['current_supply'] == '210.000 SCORUM'
    assert initdelegate['balance'] == '110.000 SCORUM'
    assert alice['balance'] == '100.000 SCORUM'


def test_transfer():
    genesis = Genesis()
    genesis["init_supply"] = 210000
    genesis.add_account(acc_name=acc_name,
                        public_key=acc_public_key,
                        scr_amount=110000,
                        witness=True)
    genesis.add_account(acc_name='alice',
                        public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                        scr_amount=100000)

    node = Node(genesis=genesis)
    node.config['witness'] = f'"{acc_name}"'
    node.config['private-key'] = acc_private_key
    node.run()
    scorum = Steem(chain_id=node.get_chain_id(), nodes=[node.addr], keys=[acc_private_key])

    alice = scorum.get_account('alice')
    print(alice)
    print(scorum.get_account(acc_name))
    scorum.commit.transfer(to='alice', amount=10000, asset='SCORUM', account=acc_name)
    alice = scorum.get_account('alice')
    print(alice)
    node.stop()



def test_budget_creation():
    genesis = Genesis()
    genesis.add_account(acc_name="initdelegate",
                        public_key="SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi",
                        scr_amount=110000,
                        witness=True)
    genesis.add_account(acc_name='alice',
                        public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                        scr_amount=100000)

    node = Node(genesis)
    node.config['witness'] = '"initdelegate"'
    node.config['privete-key'] = initdelegate_private_key
    node.run()

    rpc = RpcClient([node], node.get_chain_id())
    rpc.create_budget("initdelegate", "", "50.000 SCORUM", True)

def test_progress():
    genesis = Genesis()
    genesis.add_account(acc_name="initdelegate",
                        public_key="SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi",
                        scr_amount=110000,
                        witness=True)
    genesis.add_account(acc_name='alice',
                        public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                        scr_amount=100000)

    node = Node(genesis)
    node.config['witness'] = '"initdelegate"'
    node.config['privete-key'] = initdelegate_private_key
    node.run()

    time.sleep(3)
    rpc = RpcClient([node], node.get_chain_id())
    node.stop()


























