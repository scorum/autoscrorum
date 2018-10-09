from copy import copy

import pytest
from graphenebase.amount import Amount
from src.utils import fmt_time_from_now
from src.wallet import Wallet
from tests.advertising.conftest import update_budget_time, update_budget_balance, calc_per_block
from tests.common import (
    validate_response, validate_error_response, check_logs_on_errors, check_virt_ops,
    RE_BUDGET_NOT_EXIST, MAX_INT_64
)


def test_close_before_starttime(wallet_3hf: Wallet, budget):
    update_budget_time(wallet_3hf, budget, start=30, deadline=60)  # to delay opening time for budget
    balance_before = wallet_3hf.get_account_scr_balance(budget["owner"])
    validate_response(wallet_3hf.create_budget(**budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, budget)  # update budget params / set budget id
    response = wallet_3hf.close_budget(budget['type'], budget["id"], budget["owner"])
    validate_response(response, wallet_3hf.close_budget.__name__)
    balance_after = wallet_3hf.get_account_scr_balance(budget["owner"])
    assert balance_after == balance_before
    check_virt_ops(
        wallet_3hf, response['block_num'], response['block_num'],
        {'close_budget', 'budget_closing', 'budget_owner_income'}
    )
    assert len(wallet_3hf.get_budgets(budget['owner'], budget['type'])) == 0
    assert len(wallet_3hf.list_buddget_owners(budget_type=budget['type'])) == 0


def test_close_after_starttime(wallet_3hf: Wallet, budget):
    update_budget_time(wallet_3hf, budget)
    balance_before = wallet_3hf.get_account_scr_balance(budget["owner"])
    response = wallet_3hf.create_budget(**budget)
    validate_response(response, wallet_3hf.create_budget.__name__)
    create_block = response["block_num"]
    update_budget_balance(wallet_3hf, budget)  # update budget params / set budget id
    per_block = Amount(budget["per_block"])

    response = wallet_3hf.close_budget(budget['type'], budget["id"], budget["owner"])
    validate_response(response, wallet_3hf.close_budget.__name__)
    close_block = response["block_num"]
    balance_after = wallet_3hf.get_account_scr_balance(budget["owner"])
    assert balance_before == balance_after + per_block * (close_block - create_block)
    check_virt_ops(
        wallet_3hf, close_block, close_block,
        {'close_budget', 'budget_closing', 'budget_outgo', 'budget_owner_income'}
    )
    assert len(wallet_3hf.get_budgets(budget['owner'], budget['type'])) == 0
    assert len(wallet_3hf.list_buddget_owners(budget_type=budget['type'])) == 0


def test_close_post_vs_banner(wallet_3hf: Wallet, post_budget, banner_budget):
    new_budget = copy(post_budget)
    update_budget_time(wallet_3hf, post_budget)
    validate_response(wallet_3hf.create_budget(**post_budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, post_budget)  # update budget params / set budget id

    update_budget_time(wallet_3hf, banner_budget)
    validate_response(wallet_3hf.create_budget(**banner_budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, banner_budget)  # update budget params / set budget id

    assert post_budget["id"] == banner_budget["id"]  # both = 0

    response = wallet_3hf.close_budget(post_budget['type'], post_budget["id"], post_budget["owner"])
    validate_response(response, wallet_3hf.close_budget.__name__)

    post_budgets = wallet_3hf.get_budgets(post_budget['owner'], post_budget['type'])
    assert len(post_budgets) == 0
    banner_budgets = wallet_3hf.get_budgets(banner_budget['owner'], banner_budget['type'])
    assert len(banner_budgets) == 1

    update_budget_time(wallet_3hf, new_budget)
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


@pytest.mark.skip_long_term
@pytest.mark.parametrize('start', [0, 6])
@pytest.mark.parametrize('deadline', [6, 7, 21])
@pytest.mark.parametrize('balance', ["1.000000000 SCR", "0.000000001 SCR", "0.000000015 SCR"])
def test_deadline_close_budget(wallet_3hf: Wallet, budget, start, deadline, node, balance):
    acc_balance_before = wallet_3hf.get_account_scr_balance(budget['owner'])
    update_budget_time(wallet_3hf, budget, start=start, deadline=deadline + start)
    budget.update({"balance": balance})
    response = wallet_3hf.create_budget(**budget)
    validate_response(response, wallet_3hf.create_budget.__name__, [('block_num', int)])
    update_budget_balance(wallet_3hf, budget)

    per_block, reminder = calc_per_block(deadline, Amount(balance))
    assert per_block == Amount(budget['per_block'])

    last_block = response['block_num']
    blocks_wait = last_block + deadline // 3
    wallet_3hf.get_block(blocks_wait + 1, wait_for_block=True)
    budgets = wallet_3hf.get_user_budgets(budget['owner'])
    validate_response(budgets, wallet_3hf.get_user_budgets.__name__)
    assert 0 == len(budgets), "All budgets should be closed. %s" % fmt_time_from_now()

    virt_ops = {'budget_closing', 'budget_outgo'}
    if reminder.amount:
        virt_ops.add('budget_owner_income')
    check_virt_ops(wallet_3hf, blocks_wait - 1, blocks_wait + 1, virt_ops)

    acc_balance_after = wallet_3hf.get_account_scr_balance(budget['owner'])
    assert acc_balance_before - Amount(balance) + reminder == acc_balance_after

    node.read_logs()
    check_logs_on_errors(node.logs)
