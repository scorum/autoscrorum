import pytest
from scorum.graphenebase.amount import Amount

from src.account import Account
from src.errors import Errors
from src.genesis import Genesis
from src.wallet import Wallet
from tests.common import DEFAULT_WITNESS

test_account_memo_key = 'SCR52jUWZchsz6hVD13PzZrQP94mcbJL5seYxnm46Uk6D9tmJdGJh'
test_account_owner_pub_key = 'SCR695t7HG9WMA2HnZkPGnjQkBDXza1WQLKhztdhrN9VwqMJr3WK4'
test_accout_posting_pub_key = 'SCR8eP1ZeZGJxQNK7sRzbS5TMpmDHj6iKtNdLP2AfwV3tfq8ch1R6'
test_account_active_pub_key = 'SCR8G7CU317DiQxkq95c5poDV74nu715CbU8h3QqoNy2Rzv9wFGnj'


@pytest.mark.parametrize('valid_name', ['joe', 'ahahahahahahaha1'])
def test_create_account(wallet: Wallet, valid_name):
    fee = Amount('0.000001000 SCR')
    account_before = wallet.list_accounts()

    creator_balance_before = wallet.get_account_scr_balance(DEFAULT_WITNESS)
    print(wallet.create_account(DEFAULT_WITNESS,
                                newname=valid_name,
                                owner=test_account_owner_pub_key,
                                active=test_account_active_pub_key,
                                posting=test_accout_posting_pub_key,
                                memo=test_account_memo_key,
                                fee=fee))
    creator_balance_delta = creator_balance_before - wallet.get_account_scr_balance(DEFAULT_WITNESS)
    assert creator_balance_delta == fee

    assert wallet.get_account(valid_name)['recovery_account'] == DEFAULT_WITNESS

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
                                            ('alice', Errors.uniqueness_constraint_violated)])
def test_create_account_with_invalid_name(wallet: Wallet, name_and_error):
    invalid_name, error = name_and_error
    response = wallet.create_account(DEFAULT_WITNESS, invalid_name, test_account_owner_pub_key)
    print(response)
    assert error.value == response['error']['data']['code']


@pytest.mark.parametrize('valid_name', ['joe', 'aaaaaaaaaaaaaaa1'])
def test_create_account_by_committee(wallet: Wallet, genesis: Genesis, valid_name):
    accounts_before = wallet.list_accounts()
    creator_balance_before = wallet.get_account_scr_balance(DEFAULT_WITNESS)
    print(wallet.create_account_by_committee(DEFAULT_WITNESS,
                                             newname=valid_name,
                                             owner=test_account_owner_pub_key,
                                             active=test_account_active_pub_key,
                                             posting=test_accout_posting_pub_key,
                                             memo=test_account_memo_key, ))
    assert creator_balance_before == wallet.get_account_scr_balance(DEFAULT_WITNESS)

    assert wallet.get_account(valid_name)['recovery_account'] == DEFAULT_WITNESS

    accounts_after = wallet.list_accounts()
    assert len(accounts_after) == len(accounts_before) + 1
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
    registration_bonus_amount = genesis['registration_bonus'].split()[0]
    assert new_account_sp_balance_amount == registration_bonus_amount

    # TODO add assert to check registration_supply delta

    keys_auths = wallet.get_account_keys_auths(valid_name)
    assert keys_auths['owner'] == test_account_owner_pub_key
    assert keys_auths['active'] == test_account_active_pub_key
    assert keys_auths['posting'] == test_accout_posting_pub_key
    assert keys_auths['memo'] == test_account_memo_key


def test_registration_schedule(wallet: Wallet, genesis: Genesis):
    def expected_reward_value(schedule):
        registration_bonus = Amount(genesis['registration_bonus'])
        total_accounts = len(wallet.list_accounts())

        for s in schedule:
            if total_accounts <= s['users']:
                return registration_bonus * s['bonus_percent'] // 100
        return registration_bonus * schedule[-1]['bonus_percent'] // 100

    registration_schedule = list(genesis['registration_schedule'])
    total_users_in_schedule = 0
    for stage in registration_schedule:
        total_users_in_schedule += stage['users']
        stage['users'] = total_users_in_schedule

    names = ['martin', 'doug', 'kevin', 'joe', 'jim']
    accounts = [Account(name) for name in names]

    for account in accounts:
        wallet.create_account_by_committee(DEFAULT_WITNESS,
                                           account.name,
                                           active=account.active.get_public_key(),
                                           owner=account.owner.get_public_key(),
                                           posting=account.posting.get_public_key())

        assert wallet.get_account_sp_balance(account.name) == expected_reward_value(registration_schedule), \
            '{} sp balance differs from expected'.format(account.name)


@pytest.mark.parametrize('name_and_error', [('', Errors.assert_exception),
                                            ('\'', Errors.assert_exception),
                                            ('ab', Errors.assert_exception),
                                            ('aB1', Errors.assert_exception),
                                            ('a_b', Errors.assert_exception),
                                            ('1ab', Errors.assert_exception),
                                            ('alalalalalalalala', Errors.tx_missing_active_auth),
                                            ('alice', Errors.uniqueness_constraint_violated)])
def test_create_account_with_invalid_name_by_committee(wallet: Wallet, name_and_error):
    invalid_name, error = name_and_error
    response = wallet.create_account_by_committee(DEFAULT_WITNESS, invalid_name, test_account_owner_pub_key)
    print(response)
    assert error.value == response['error']['data']['code']
