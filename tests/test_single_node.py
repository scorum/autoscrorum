from graphenebase.amount import Amount

acc_name = "initdelegate"
acc_public_key = "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
acc_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


def test_block_production(wallet, node):
    block = wallet.get_block(1)

    assert block['witness'] == node.config['witness'][1:-1]


def test_genesis_block(wallet):
    initdelegate = wallet.get_account("initdelegate")
    alice = wallet.get_account("alice")
    info = wallet.get_dynamic_global_properties()

    assert info['total_supply'] == '1210600.100000000 SCR'
    assert initdelegate['balance'] == '110000.000000000 SCR'
    assert alice['balance'] == '100000.000000000 SCR'


def test_transfer(wallet):
    initdelegate_balance_before = Amount(wallet.get_account('initdelegate')['balance'])
    amount = initdelegate_balance_before - 100
    alice_balance_before = Amount(wallet.get_account('alice')['balance'])

    wallet.transfer('initdelegate', 'alice', amount)

    initdelegate_balance_after = Amount(wallet.get_account('initdelegate')['balance'])
    alice_balance_after = Amount(wallet.get_account('alice')['balance'])

    assert initdelegate_balance_after == initdelegate_balance_before - amount
    assert alice_balance_after == alice_balance_before + amount


def test_transfer_invalid_amount(wallet):
    initdelegate_balance_before = Amount(wallet.get_account('initdelegate')['balance'])
    amount = initdelegate_balance_before + 1
    alice_balance_before = Amount(wallet.get_account('alice')['balance'])

    response = wallet.transfer('initdelegate', 'alice', amount)

    initdelegate_balance_after = Amount(wallet.get_account('initdelegate')['balance'])
    alice_balance_after = Amount(wallet.get_account('alice')['balance'])

    assert initdelegate_balance_after == initdelegate_balance_before
    assert alice_balance_after == alice_balance_before

    assert 'Account does not have sufficient funds for transfer' in response['error']['message']


def test_transfer_to_vesting(wallet):
    initdelegate_scr_balance_before = Amount(wallet.get_account('initdelegate')['balance'])
    alice_sp_balance_before = Amount(wallet.get_account('alice')['vesting_shares'])

    amount = 1

    wallet.transfer_to_vesting('initdelegate', 'alice', amount)

    initdelegate_scr_balance_after = Amount(wallet.get_account('initdelegate')['balance'])
    alice_sp_balance_after = Amount(wallet.get_account('alice')['vesting_shares'])

    assert initdelegate_scr_balance_after == initdelegate_scr_balance_before - amount
    assert alice_sp_balance_after == alice_sp_balance_before + amount


def test_create_account(wallet):
    test_account_name = 'joe'
    test_account_pub_key = 'SCR4tp1i6hGuefvYWSdPXPC3f959XLgLiXtBpbfQCkTK9sjcA4qWZ'

    wallet.create_account('initdelegate', newname=test_account_name, owner=test_account_pub_key)

    accounts = wallet.list_accounts()

    assert(len(accounts) == 4)

    assert(test_account_name in accounts)
