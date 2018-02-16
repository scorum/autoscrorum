acc_name = "initdelegate"
acc_public_key = "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
acc_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


def test_block_production(rpc, node):
    block = rpc.get_block(1)

    assert block['witness'] == node.config['witness'][1:-1]


def test_genesis_block(rpc):
    initdelegate = rpc.get_account("initdelegate")
    alice = rpc.get_account("alice")
    info = rpc.get_dynamic_global_properties()

    assert info['total_supply'] == '1210100.000000000 SCR'
    assert initdelegate['balance'] == '110000.000000000 SCR'
    assert alice['balance'] == '100000.000000000 SCR'


def test_transfer_invalid_amount(rpc):
    initdelegate_balance_before = float(rpc.get_account('initdelegate')['balance'].split()[0])
    amount = int(initdelegate_balance_before + 1)
    alice_balance_before = float(rpc.get_account('alice')['balance'].split()[0])

    response = rpc.transfer('initdelegate', 'alice', amount)

    initdelegate_balance_after = float(rpc.get_account('initdelegate')['balance'].split()[0])
    alice_balance_after = float(rpc.get_account('alice')['balance'].split()[0])

    assert initdelegate_balance_after == initdelegate_balance_before
    assert alice_balance_after == alice_balance_before

    assert 'Account does not have sufficient funds for transfer' in response['error']['message']


def test_transfer_to_vesting(rpc):
    initdelegate_scr_balance_before = float(rpc.get_account('initdelegate')['balance'].split()[0])
    alice_sp_balance_before = float(rpc.get_account('alice')['vesting_shares'].split()[0])

    amount = 1

    rpc.transfer_to_vesting('initdelegate', 'alice', amount)

    initdelegate_scr_balance_after = float(rpc.get_account('initdelegate')['balance'].split()[0])
    alice_sp_balance_after = float(rpc.get_account('alice')['vesting_shares'].split()[0])

    assert initdelegate_scr_balance_after == initdelegate_scr_balance_before - amount
    assert alice_sp_balance_after == alice_sp_balance_before + amount


def test_create_account(rpc):
    test_account_name = 'bob'
    test_account_pub_key = 'SCR7w8tySAVQmJ95xSL8SS2GJJCws9s2gCY85DSAEALMFPmaMKA6p'

    rpc.create_account('initdelegate', newname=test_account_name, owner=test_account_pub_key)

    accounts = rpc.list_accounts()

    assert(len(accounts) == 3)

    assert(test_account_name in accounts)
