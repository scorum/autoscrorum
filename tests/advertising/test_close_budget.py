from copy import copy

import pytest
from graphenebase.amount import Amount
from src.utils import fmt_time_from_now
from src.wallet import Wallet
from tests.advertising.conftest import update_budget_time, update_budget_balance
from tests.common import (
    validate_response, validate_error_response, check_logs_on_errors, check_virt_ops,
    RE_BUDGET_NOT_EXIST, MAX_INT_64
)


def test_close_before_starttime(wallet_3hf: Wallet, budget):
    update_budget_time(budget, start=30, deadline=60)  # to delay opening time for budget
    budget_balance = Amount(budget["balance"])
    balance_before = wallet_3hf.get_account_scr_balance(budget["owner"])

    validate_response(wallet_3hf.create_budget(**budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, budget)  # update budget params / set budget id

    balance_after_create = wallet_3hf.get_account_scr_balance(budget["owner"])

    assert balance_before - balance_after_create == budget_balance

    response = wallet_3hf.close_budget(budget['type'], budget["id"], budget["owner"])
    validate_response(response, wallet_3hf.close_budget.__name__)

    balance_after_close = wallet_3hf.get_account_scr_balance(budget["owner"])
    assert balance_after_close == balance_after_create + budget_balance

    check_virt_ops(
        wallet_3hf, response['block_num'], response['block_num'],
        {'closing_budget', 'cash_back_from_advertising_budget_to_owner'}
    )


def test_close_after_starttime(wallet_3hf: Wallet, budget):
    update_budget_time(budget)
    budget_balance = Amount(budget["balance"])
    balance_before = wallet_3hf.get_account_scr_balance(budget["owner"])

    response = wallet_3hf.create_budget(**budget)
    validate_response(response, wallet_3hf.create_budget.__name__)
    create_block = response["block_num"]
    update_budget_balance(wallet_3hf, budget)  # update budget params / set budget id
    per_block = Amount(budget["per_block"])

    balance_after_create = wallet_3hf.get_account_scr_balance(budget["owner"])

    assert balance_before - balance_after_create == budget_balance

    response = wallet_3hf.close_budget(budget['type'], budget["id"], budget["owner"])
    validate_response(response, wallet_3hf.close_budget.__name__)
    close_block = response["block_num"]

    balance_after_close = wallet_3hf.get_account_scr_balance(budget["owner"])
    assert balance_after_close == balance_after_create + budget_balance - per_block * (close_block - create_block)

    check_virt_ops(
        wallet_3hf, close_block, close_block,
        {
            'closing_budget', 'cash_back_from_advertising_budget_to_owner',
            'allocate_cash_from_advertising_budget'
        }
    )


def test_close_post_vs_banner(wallet_3hf: Wallet, post_budget, banner_budget):
    new_budget = copy(post_budget)
    update_budget_time(post_budget)
    validate_response(wallet_3hf.create_budget(**post_budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, post_budget)  # update budget params / set budget id

    update_budget_time(banner_budget)
    validate_response(wallet_3hf.create_budget(**banner_budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, banner_budget)  # update budget params / set budget id

    assert post_budget["id"] == banner_budget["id"]  # both = 0

    response = wallet_3hf.close_budget(post_budget['type'], post_budget["id"], post_budget["owner"])
    validate_response(response, wallet_3hf.close_budget.__name__)

    banner_budgets = wallet_3hf.get_budgets(banner_budget['owner'], banner_budget['type'])
    assert len(banner_budgets) == 1

    update_budget_time(new_budget)
    validate_response(wallet_3hf.create_budget(**new_budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, new_budget)  # update budget params / set budget id
    assert new_budget["id"] > banner_budget["id"], "Newly created budget should have incremented index"


def test_close_budgets(wallet_3hf: Wallet, opened_budgets_same_acc):
    budgets = opened_budgets_same_acc  # just renaming
    validate_response(
        wallet_3hf.close_budget(budgets[0]["type"], budgets[0]["id"], budgets[0]["owner"]),
        wallet_3hf.close_budget.__name__
    )

    rest_budgets = wallet_3hf.get_budgets(budgets[-1]["owner"], budgets[-1]["type"])
    assert len(rest_budgets) == len(budgets) - 1
    assert all(rb["id"] != budgets[0]["id"] for rb in rest_budgets)
    # delete already deleted
    validate_error_response(
        wallet_3hf.close_budget(budgets[0]['type'], budgets[0]["id"], budgets[0]["owner"]),
        wallet_3hf.close_budget.__name__,
        RE_BUDGET_NOT_EXIST
    )


@pytest.mark.parametrize('index', [-1, MAX_INT_64])
def test_invalid_idx(wallet_3hf: Wallet, opened_budgets, index):
    validate_error_response(
        wallet_3hf.close_budget(opened_budgets[0]["type"], index, opened_budgets[0]["owner"]),
        wallet_3hf.close_budget.__name__,
        RE_BUDGET_NOT_EXIST
    )


@pytest.mark.parametrize('start', [0, 6])
@pytest.mark.parametrize('deadline', [6, 7, 21])
@pytest.mark.parametrize('balance', ["1.000000000 SCR", "0.000000001 SCR", "0.000000015 SCR"])
def test_deadline_close_budget(wallet_3hf: Wallet, budget, start, deadline, node, balance):
    acc_balance_before = wallet_3hf.get_account_scr_balance(budget['owner'])
    update_budget_time(budget, start=start, deadline=start+deadline)
    budget.update({"balance": balance})
    response = wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)
    validate_response(response, wallet_3hf.create_budget.__name__, [('block_num', int)])
    last_block = response['block_num']

    blocks_wait = last_block + (deadline + start) // 3
    wallet_3hf.get_block(blocks_wait + 1, wait_for_block=True)
    budgets = wallet_3hf.get_user_budgets(budget['owner'])
    validate_response(budgets, wallet_3hf.get_user_budgets.__name__)
    assert 0 == len(budgets), "All budgets should be closed. %s" % fmt_time_from_now()
    acc_balance_after = wallet_3hf.get_account_scr_balance(budget['owner'])
    assert acc_balance_before - Amount(balance) == acc_balance_after
    check_virt_ops(
        wallet_3hf, blocks_wait - 1, blocks_wait + 1,
        {'allocate_cash_from_advertising_budget', 'closing_budget'}
    )
    node.read_logs()
    check_logs_on_errors(node.logs)
