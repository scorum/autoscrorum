from graphenebase.amount import Amount
from src.wallet import Wallet
from tests.common import expect, assert_expectations


def test_circulation_capital_equal_sum_accounts_balances(wallet: Wallet):
    accs_sp = Amount("0 SP")
    accs_scr = Amount("0 SCR")
    names = wallet.list_accounts()
    accs = wallet.get_accounts(names)
    for acc in accs:
        accs_scr += Amount(acc["balance"])
        accs_sp += Amount(acc["scorumpower"])
    accs_cc = accs_scr + accs_sp
    print("Accs - total SCR: %s, total SP: %s, sum: %s" % (str(accs_scr), str(accs_sp), str(accs_cc)))

    chain_capital = wallet.get_chain_capital()
    chain_cc = Amount(chain_capital["circulating_capital"])
    chain_sp = Amount(chain_capital["total_scorumpower"])
    chain_scr = Amount(chain_capital["total_scr"])
    print("Chain capital - total SCR: %s, total SP: %s, sum: %s" % (str(chain_scr), str(chain_sp), str(chain_cc)))

    expect(accs_sp == chain_sp)
    expect(accs_scr == chain_scr)
    expect(accs_cc == chain_cc)
    assert_expectations()


def test_circulation_capital_fields_sum(wallet: Wallet):
    scr_summands = [
        "active_voters_balancer_scr", "content_balancer_scr", "content_reward_fund_scr_balance",
        "dev_pool_scr_balance", "registration_pool_balance", "total_scr"
    ]

    sp_summands = [
        "active_voters_balancer_sp", "fund_budget_balance", "content_reward_fifa_world_cup_2018_bounty_fund_sp_balance",
        "content_reward_fund_sp_balance", "dev_pool_sp_balance", "witness_reward_in_sp_migration_fund",
        "total_scorumpower"
    ]

    chain_capital = wallet.get_chain_capital()
    circulating_scr = sum([Amount(chain_capital[s]) for s in scr_summands], Amount("0 SCR"))
    circulating_sp = sum([Amount(chain_capital[s]) for s in sp_summands], Amount("0 SP"))

    expect(circulating_scr == Amount(chain_capital["circulating_scr"]))
    expect(circulating_sp == Amount(chain_capital["circulating_sp"]))
    expect(circulating_scr + circulating_sp == Amount(chain_capital["total_supply"]))
    assert_expectations()


def test_transfer(wallet: Wallet):
    initdelegate_balance_before = wallet.get_account_scr_balance('initdelegate')
    amount = initdelegate_balance_before - Amount('5.000000000 SCR')
    alice_balance_before = wallet.get_account_scr_balance('alice')

    print(wallet.transfer('initdelegate', 'alice', amount))

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

    wallet.transfer_to_scorumpower('initdelegate', 'alice', amount)

    initdelegate_scr_balance_after = wallet.get_account_scr_balance('initdelegate')
    alice_sp_balance_after = wallet.get_account_sp_balance('alice')

    assert initdelegate_scr_balance_after == initdelegate_scr_balance_before - amount
    assert alice_sp_balance_after == alice_sp_balance_before + amount
