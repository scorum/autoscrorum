import pytest

from graphenebase.amount import Amount
from autoscorum.wallet import Wallet
from autoscorum.node import Node
from autoscorum.utils import fmt_time_from_now
from autoscorum.genesis import Genesis
from autoscorum.errors import Errors

account_name = "initdelegate"
account_public_key = "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
account_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


def test_block_production(wallet: Wallet, node: Node):
    block = wallet.get_block(1)

    assert block['witness'] == node.config['witness'][1:-1]


def test_genesis_block(wallet: Wallet, genesis: Genesis):
    info = wallet.get_dynamic_global_properties()

    expected_total_supply = (Amount(genesis['accounts_supply']) +
                             Amount(genesis['rewards_supply']) +
                             Amount(genesis['registration_supply']) +
                             Amount(genesis['founders_supply']) +
                             Amount(genesis['steemit_bounty_accounts_supply']))

    assert Amount(info['total_supply']) == expected_total_supply
    assert wallet.get_account_scr_balance(account_name) == Amount('110000.000000000 SCR')
    assert wallet.get_account_scr_balance('alice') == Amount('100000.000000000 SCR')


def test_transfer(wallet: Wallet):
    initdelegate_balance_before = wallet.get_account_scr_balance('initdelegate')
    amount = initdelegate_balance_before - Amount('100.000000000 SCR')
    alice_balance_before = wallet.get_account_scr_balance('alice')

    wallet.transfer('initdelegate', 'alice', amount)

    initdelegate_balance_after = wallet.get_account_scr_balance('initdelegate')
    alice_balance_after = wallet.get_account_scr_balance('alice')

    assert initdelegate_balance_after == initdelegate_balance_before - amount
    assert alice_balance_after == alice_balance_before + amount


def test_transfer_invalid_amount(wallet: Wallet):
    initdelegate_balance_before = wallet.get_account_scr_balance('initdelegate')
    amount = initdelegate_balance_before + Amount('0.000000001 SCR')
    alice_balance_before = wallet.get_account_scr_balance('alice')

    response = wallet.transfer('initdelegate', 'alice', amount)

    initdelegate_balance_after = wallet.get_account_scr_balance('initdelegate')
    alice_balance_after = wallet.get_account_scr_balance('alice')

    assert initdelegate_balance_after == initdelegate_balance_before
    assert alice_balance_after == alice_balance_before

    assert 'Account does not have sufficient funds for transfer' in response['error']['message']


def test_transfer_to_vesting(wallet: Wallet):
    initdelegate_scr_balance_before = wallet.get_account_scr_balance('initdelegate')
    alice_sp_balance_before = wallet.get_account_sp_balance('alice')

    amount = Amount('1.000000000 SCR')

    wallet.transfer_to_vesting('initdelegate', 'alice', amount)

    initdelegate_scr_balance_after = wallet.get_account_scr_balance('initdelegate')
    alice_sp_balance_after = wallet.get_account_sp_balance('alice')

    assert initdelegate_scr_balance_after == initdelegate_scr_balance_before - amount
    assert alice_sp_balance_after == alice_sp_balance_before + amount


test_account_memo_key = 'SCR52jUWZchsz6hVD13PzZrQP94mcbJL5seYxnm46Uk6D9tmJdGJh'
test_account_owner_pub_key = 'SCR695t7HG9WMA2HnZkPGnjQkBDXza1WQLKhztdhrN9VwqMJr3WK4'
test_accout_posting_pub_key = 'SCR8eP1ZeZGJxQNK7sRzbS5TMpmDHj6iKtNdLP2AfwV3tfq8ch1R6'
test_account_active_pub_key = 'SCR8G7CU317DiQxkq95c5poDV74nu715CbU8h3QqoNy2Rzv9wFGnj'


@pytest.mark.parametrize('valid_name', ['joe', 'ahahahahahahaha1'])
def test_create_account(wallet: Wallet, valid_name):
    creator = account_name
    fee = Amount('0.000001000 SCR')
    account_before = wallet.list_accounts()

    creator_balance_before = wallet.get_account_scr_balance(creator)
    print(wallet.create_account(creator,
                                newname=valid_name,
                                owner=test_account_owner_pub_key,
                                active=test_account_active_pub_key,
                                posting=test_accout_posting_pub_key,
                                memo=test_account_memo_key,
                                fee=fee))
    creator_balance_delta = creator_balance_before - wallet.get_account_scr_balance(creator)
    assert creator_balance_delta == fee

    assert wallet.get_account(valid_name)['recovery_account'] == creator

    accounts_after = wallet.list_accounts()
    assert len(accounts_after) == len(account_before) + 1
    assert valid_name in accounts_after

    account_by_active_key = wallet.get_account_by_key(test_account_active_pub_key)[0][0]
    assert account_by_active_key == valid_name

    account_by_posting_key = wallet.get_account_by_key(test_accout_posting_pub_key)[0][0]
    assert account_by_posting_key == valid_name

    account_by_owner_key = wallet.get_account_by_key(test_account_owner_pub_key)[0][0]
    assert account_by_owner_key == valid_name

    account_by_memo_key = wallet.get_account_by_key(test_account_memo_key)[0]
    assert account_by_memo_key == []

    new_account_sp_balance_amount = str(wallet.get_account_sp_balance(valid_name)).split()[0]
    fee_amount = str(fee).split()[0]
    assert new_account_sp_balance_amount == fee_amount

    keys_auths = wallet.get_account_keys_auths(valid_name)
    assert keys_auths['owner'] == test_account_owner_pub_key
    assert keys_auths['active'] == test_account_active_pub_key
    assert keys_auths['posting'] == test_accout_posting_pub_key
    assert keys_auths['memo'] == test_account_memo_key


@pytest.mark.parametrize('name_and_error', [('', Errors.assert_exception),
                                            ('\'', Errors.assert_exception),
                                            ('ab', Errors.assert_exception),
                                            ('aB1', Errors.assert_exception),
                                            ('a_b', Errors.assert_exception),
                                            ('1ab', Errors.assert_exception),
                                            ('alalalalalalalala', Errors.tx_missing_active_auth),
                                            ('alice', Errors.assert_exception)])
def test_create_account_with_invalid_name(wallet: Wallet, name_and_error):
    creator = account_name
    invalid_name, error = name_and_error
    response = wallet.create_account(creator, invalid_name, test_account_owner_pub_key)
    print(response)
    assert error.value == response['error']['data']['code']


@pytest.mark.parametrize('valid_name', ['joe', 'aaaaaaaaaaaaaaa1'])
def test_create_account_by_committee(wallet: Wallet, genesis: Genesis, valid_name):
    creator = account_name

    creator_balance_before = wallet.get_account_scr_balance(creator)
    print(wallet.create_account_by_committee(creator,
                                             newname=valid_name,
                                             owner=test_account_owner_pub_key,
                                             active=test_account_active_pub_key,
                                             posting=test_accout_posting_pub_key,
                                             memo=test_account_memo_key,))
    assert creator_balance_before == wallet.get_account_scr_balance(creator)

    assert wallet.get_account(valid_name)['recovery_account'] == creator

    accounts = wallet.list_accounts()
    assert len(accounts) == 4
    assert valid_name in accounts

    account_by_active_key = wallet.get_account_by_key(test_account_active_pub_key)[0][0]
    assert account_by_active_key == valid_name

    account_by_posting_key = wallet.get_account_by_key(test_accout_posting_pub_key)[0][0]
    assert account_by_posting_key == valid_name

    account_by_owner_key = wallet.get_account_by_key(test_account_owner_pub_key)[0][0]
    assert account_by_owner_key == valid_name

    account_by_memo_key = wallet.get_account_by_key(test_account_memo_key)[0]
    assert account_by_memo_key == []

    new_account_sp_balance_amount = str(wallet.get_account_sp_balance(valid_name)).split()[0]
    registration_bouns_amount = genesis['registration_bonus'].split()[0]
    assert new_account_sp_balance_amount == registration_bouns_amount

    # TODO add assert to check registration_supply delta

    keys_auths = wallet.get_account_keys_auths(valid_name)
    assert keys_auths['owner'] == test_account_owner_pub_key
    assert keys_auths['active'] == test_account_active_pub_key
    assert keys_auths['posting'] == test_accout_posting_pub_key
    assert keys_auths['memo'] == test_account_memo_key


@pytest.mark.parametrize('name_and_error', [('', Errors.assert_exception),
                                            ('\'', Errors.assert_exception),
                                            ('ab', Errors.assert_exception),
                                            ('aB1', Errors.assert_exception),
                                            ('a_b', Errors.assert_exception),
                                            ('1ab', Errors.assert_exception),
                                            ('alalalalalalalala', Errors.tx_missing_active_auth),
                                            ('alice', Errors.assert_exception)])
def test_create_account_with_invalid_name_by_committee(wallet: Wallet, name_and_error):
    creator = account_name
    invalid_name, error = name_and_error
    response = wallet.create_account_by_committee(creator, invalid_name, test_account_owner_pub_key)
    assert error.value == response['error']['data']['code']


def test_create_budget(wallet: Wallet):
    wallet.create_budget(account_name, Amount("10666.666666667 SCR"), fmt_time_from_now(30))
    budget = wallet.get_budgets(account_name)[0]

    assert account_name in wallet.list_buddget_owners()
    assert budget['per_block'] == '1000000000000'
    assert budget['owner'] == account_name
