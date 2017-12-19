import time

from autoscorum.node import Node
from autoscorum.genesis import Genesis
from autoscorum.rpc_client import RpcClient

default_genesis = {
    "initial_timestamp": "2017-11-29T10:03:00",
    "init_supply": 1000,
    "init_rewards_supply": "1000000.000 SCORUM",
    "accounts": [{
        "name": "initdelegate",
        "recovery_account": "",
        "public_key": "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi",
        "scr_amount": 1000,
        "sp_amount": 0
    }, {
        "name": "alice",
        "recovery_account": "",
        "public_key": "SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
        "scr_amount": 0,
        "sp_amount": 0
    }, {
        "name": "bob",
        "recovery_account": "",
        "public_key": "SCR7w8tySAVQmJ95xSL8SS2GJJCws9s2gCY85DSAEALMFPmaMKA6p",
        "scr_amount": 0,
        "sp_amount": 0
    }],

    "witness_candidates": [{
        "owner_name": "initdelegate",
        "block_signing_key": "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
    }, {
        "owner_name": "alice",
        "block_signing_key": "SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx"
    }, {
        "owner_name": "bob",
        "block_signing_key": "SCR7w8tySAVQmJ95xSL8SS2GJJCws9s2gCY85DSAEALMFPmaMKA6p"
    }]
}

initdelegate_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


def test_block_production():
    genesis = Genesis()
    genesis["init_supply"] = 10000
    genesis.add_account(acc_name="initdelegate",
                        public_key="SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi",
                        scr_amount=10000,
                        witness=True)

    initdelegate = Node(genesis=genesis)
    initdelegate.config['witness'] = '"initdelegate"'
    initdelegate.config['private-key'] = initdelegate_private_key

    initdelegate.run()
    rpc = RpcClient([initdelegate])
    block = rpc.get_block(1)
    initdelegate.stop()

    assert block['witness'] == initdelegate.config['witness'][1:-1]


def test_genesis_block():
    genesis = Genesis()
    genesis["init_supply"] = 210000
    genesis.add_account(acc_name="initdelegate",
                        public_key="SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi",
                        scr_amount=110000,
                        witness=True)
    genesis.add_account(acc_name='alice',
                        public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                        scr_amount=100000)

    node = Node(genesis=genesis)
    node.config['witness'] = '"initdelegate"'
    node.config['private-key'] = initdelegate_private_key
    node.run()

    rpc = RpcClient([node])
    initdelegate = rpc.get_account("initdelegate")
    alice = rpc.get_account("alice")
    info = rpc.get_info()
    node.stop()

    assert info['current_supply'] == '210.000 SCORUM'
    assert initdelegate[0]['balance'] == '110.000 SCORUM'
    assert alice[0]['balance'] == '100.000 SCORUM'


def test_witness_reward():
    witness = Node(genesis=default_genesis)
    witness.config['witness'] = '"initdelegate"'
    witness.config['private-key'] = initdelegate_private_key
    witness.run()

    rpc = RpcClient([witness])


























