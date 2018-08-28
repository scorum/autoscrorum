import pytest
import time

from graphenebase.amount import Amount
from src.wallet import Wallet
from tests.common import expect, assert_expectations, DEFAULT_WITNESS, apply_hardfork, validate_response


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


accounts_amounts = [
    (DEFAULT_WITNESS, Amount("10.000000000 SP")), ("alice", Amount("20.000000000 SP")),
    ("bob", Amount("50.000000000 SP"))
]


@pytest.mark.parametrize("account,amount", accounts_amounts)
def test_account_active_withdraw(wallet: Wallet, account, amount):
    response = wallet.withdraw(account, amount)

    validate_response(response, wallet.withdraw.__name__)

    transfers = wallet.get_account_transfers(account)

    expect(len(transfers) == 1, "Was created more withdrawals then was expected.")

    withdraw = transfers[0][1]

    expect(withdraw["status"] == "active")
    expect(Amount(withdraw["withdrawn"]) == Amount("0 SP"))  # e.g. any payment was not provided yet
    expect(withdraw["op"][0] == "withdraw_scorumpower")
    expect(Amount(withdraw["op"][1]["scorumpower"]) == amount)
    expect(withdraw["op"][1]["account"] == account)
    assert_expectations()


@pytest.mark.parametrize("account,amount", accounts_amounts)
def test_account_zero_withdraw(wallet: Wallet, account, amount):
    response = wallet.withdraw(account, amount)
    validate_response(response, wallet.withdraw.__name__)

    response = wallet.withdraw(account, Amount("0 SP"))
    validate_response(response, wallet.withdraw.__name__)

    transfers = wallet.get_account_transfers(account)
    expect(len(transfers) == 2, "Was created more withdrawals then was expected.")
    expect(transfers[0][1]["status"] == "interrupted")
    expect(transfers[1][1]["status"] == "empty")
    assert_expectations()


@pytest.mark.skip("On production this test will take a year. Run it only manually.")
@pytest.mark.parametrize("account,amount", [accounts_amounts[1]])
def test_account_final_withdraw(wallet: Wallet, account, amount):
    response = wallet.withdraw(account, amount)
    validate_response(response, wallet.withdraw.__name__)

    account_before = wallet.get_account(account)

    constants = wallet.get_config()
    intervals = constants["SCORUM_VESTING_WITHDRAW_INTERVALS"]

    single_payment = amount / intervals

    interval_sec = constants["SCORUM_VESTING_WITHDRAW_INTERVAL_SECONDS"]

    for i in range(1, intervals + 1):
        time.sleep(interval_sec + 1)

        expected_withdraw = single_payment * i

        transfers = wallet.get_account_transfers(account)
        expect(len(transfers) == 1, "Was created more withdrawals then was expected.")

        withdrawn = Amount(transfers[0][1]["withdrawn"])
        expect(withdrawn == expected_withdraw, "step: %d, actual '%s', expected '%s'" % (i, withdrawn, expected_withdraw))

        account_after = wallet.get_account(account)
        sp_change = Amount(account_before["scorumpower"]) - Amount(account_after["scorumpower"])
        expect(sp_change == expected_withdraw, "step: %d, actual '%s', expected '%s'" % (i, sp_change, expected_withdraw))

        scr_change = Amount(account_after["balance"]) - Amount(account_before["balance"])
        expect(scr_change == expected_withdraw, "step: %d, actual '%s', expected '%s'" % (i, scr_change, expected_withdraw))

        assert_expectations()

        if i == intervals:
            assert transfers[0][1]["status"] == "finished"


def test_devcommittee_active_withdraw(wallet: Wallet):
    amount = Amount("10.000000000 SP")

    response = wallet.withdraw_vesting(DEFAULT_WITNESS, amount)
    validate_response(response, wallet.withdraw_vesting.__name__)

    proposals = wallet.list_proposals()
    validate_response(response, wallet.list_proposals.__name__)
    expect(len(proposals) == 1, "Was created %d proposals, expected only one: %s" % (len(proposals), proposals))

    proposal_id = proposals[0]["id"]
    response = wallet.proposal_vote(DEFAULT_WITNESS, proposal_id)
    validate_response(response, wallet.proposal_vote.__name__)

    transfers = wallet.get_devcommittee_transfers()
    validate_response(transfers, wallet.get_devcommittee_transfers.__name__)
    expect(len(transfers) == 1, "Was created more transfers then was expected.")

    print(transfers)
    withdraw = transfers[0]

    expect(withdraw["status"] == "active")
    expect(Amount(withdraw["withdrawn"]) == Amount("0 SP"))  # e.g. any payment was not provided yet
    expect(withdraw["op"][0] == "proposal_virtual")
    expect(withdraw["op"][1]["proposal_op"][0] == "development_committee_withdraw_vesting")
    expect(Amount(withdraw["op"][1]["proposal_op"][1]["vesting_shares"]) == amount)
    assert_expectations()


def test_devcommittee_zero_withdraw_2hf(wallet: Wallet):
    # on prev HF zero-withdraw was not allowed for devcommittee
    apply_hardfork(wallet, 2)

    amount = Amount("99.000000000 SP")
    response = wallet.withdraw_vesting(DEFAULT_WITNESS, amount)
    validate_response(response, wallet.withdraw_vesting.__name__)

    proposals = wallet.list_proposals()
    validate_response(response, wallet.list_proposals.__name__)
    expect(len(proposals) == 1, "Was created %d proposals, expected only one: %s" % (len(proposals), proposals))

    proposal_id = proposals[0]["id"]
    response = wallet.proposal_vote(DEFAULT_WITNESS, proposal_id)
    validate_response(response, wallet.proposal_vote.__name__)

    response = wallet.withdraw_vesting(DEFAULT_WITNESS, Amount("0 SP"))
    validate_response(response, wallet.withdraw_vesting.__name__)

    proposals = wallet.list_proposals()
    validate_response(response, wallet.list_proposals.__name__)
    expect(len(proposals) == 1, "Was created %d proposals, expected one: %s" % (len(proposals), proposals))

    proposal_id = proposals[0]["id"]
    response = wallet.proposal_vote(DEFAULT_WITNESS, proposal_id)
    validate_response(response, wallet.proposal_vote.__name__)

    transfers = wallet.get_devcommittee_transfers()
    validate_response(transfers, wallet.get_devcommittee_transfers.__name__)
    expect(len(transfers) == 2, "Was created unexpected amount of transfers.")
    expect(transfers[0]["status"] == "empty")
    expect(transfers[1]["status"] == "interrupted")
    assert_expectations()
