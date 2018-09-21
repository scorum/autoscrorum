from copy import copy

import pytest
from graphenebase.amount import Amount
from src.wallet import Wallet
from tests.advertising.conftest import update_budget_time, empower_advertising_moderator, update_budget_balance
from tests.common import DEFAULT_WITNESS, validate_response, validate_error_response, RE_IDX_OUT_OF_RANGE, MAX_INT_64


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_before_starttime(wallet: Wallet, budget, moderator):
    update_budget_time(budget, start=30, deadline=60)  # to delay opening time for budget
    budget_balance = Amount(budget["balance"])
    balance_before = wallet.get_account_scr_balance(budget["owner"])

    validate_response(wallet.create_budget(**budget), wallet.create_budget.__name__)
    update_budget_balance(wallet, budget)  # update budget params / set budget id

    balance_after_create = wallet.get_account_scr_balance(budget["owner"])

    assert balance_before - balance_after_create == budget_balance

    empower_advertising_moderator(wallet, moderator)
    response = wallet.close_budget_by_advertising_moderator(moderator, budget["id"], budget["type"])
    validate_response(response, wallet.close_budget_by_advertising_moderator.__name__)

    balance_after_close = wallet.get_account_scr_balance(budget["owner"])
    assert balance_after_close == balance_after_create + budget_balance


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_after_starttime(wallet: Wallet, budget, moderator):
    update_budget_time(budget)
    budget_balance = Amount(budget["balance"])
    balance_before = wallet.get_account_scr_balance(budget["owner"])

    response = wallet.create_budget(**budget)
    validate_response(response, wallet.create_budget.__name__)
    create_block = response["block_num"]
    update_budget_balance(wallet, budget)  # update budget params / set budget id
    per_block = Amount(budget["per_block"])

    balance_after_create = wallet.get_account_scr_balance(budget["owner"])

    assert balance_before - balance_after_create == budget_balance

    empower_advertising_moderator(wallet, moderator)
    response = wallet.close_budget_by_advertising_moderator(moderator, budget["id"], budget["type"])
    validate_response(response, wallet.close_budget_by_advertising_moderator.__name__)
    close_block = response["block_num"]

    balance_after_close = wallet.get_account_scr_balance(budget["owner"])
    assert balance_after_close == balance_after_create + budget_balance - per_block * (close_block - create_block)


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_post_vs_banner(wallet: Wallet, moderator, post_budget, banner_budget):
    new_budget = copy(post_budget)
    update_budget_time(post_budget)
    validate_response(wallet.create_budget(**post_budget), wallet.create_budget.__name__)
    update_budget_balance(wallet, post_budget)  # update budget params / set budget id

    update_budget_time(banner_budget)
    validate_response(wallet.create_budget(**banner_budget), wallet.create_budget.__name__)
    update_budget_balance(wallet, banner_budget)  # update budget params / set budget id

    assert post_budget["id"] == banner_budget["id"]  # both = 0

    empower_advertising_moderator(wallet, moderator)
    response = wallet.close_budget_by_advertising_moderator(moderator, post_budget["id"], post_budget["type"])
    validate_response(response, wallet.close_budget_by_advertising_moderator.__name__)

    banner_budgets = wallet.get_budgets(banner_budget['owner'], banner_budget['type'])
    assert len(banner_budgets) == 1

    update_budget_time(new_budget)
    validate_response(wallet.create_budget(**new_budget), wallet.create_budget.__name__)
    update_budget_balance(wallet, new_budget)  # update budget params / set budget id
    assert new_budget["id"] > banner_budget["id"], "Newly created budget should have incremented index"


@pytest.mark.parametrize('moderator', ['alice', 'bob', DEFAULT_WITNESS])
def test_close_budgets(wallet: Wallet, moderator, opened_budgets_same_acc):
    budgets = opened_budgets_same_acc  # just renaming
    empower_advertising_moderator(wallet, moderator)
    validate_response(
        wallet.close_budget_by_advertising_moderator(moderator, budgets[0]["id"], budgets[0]["type"]),
        wallet.close_budget_by_advertising_moderator.__name__
    )

    rest_budgets = wallet.get_budgets(budgets[-1]["owner"], budgets[-1]["type"])
    assert len(rest_budgets) == len(budgets) - 1
    assert all(rb["id"] != budgets[0]["id"] for rb in rest_budgets)
    # delete already deleted
    validate_error_response(
        wallet.close_budget_by_advertising_moderator(moderator, budgets[0]["id"], budgets[0]["type"]),
        wallet.close_budget_by_advertising_moderator.__name__,
        RE_IDX_OUT_OF_RANGE
    )


@pytest.mark.parametrize('moderator', ['alice', 'bob', DEFAULT_WITNESS])
@pytest.mark.parametrize('index', [-1, MAX_INT_64])
def test_invalid_idx(wallet: Wallet, moderator, opened_budgets, index):
    empower_advertising_moderator(wallet, moderator)
    validate_error_response(
        wallet.close_budget_by_advertising_moderator(moderator, index, opened_budgets[0]["type"]),
        wallet.close_budget_by_advertising_moderator.__name__,
        RE_IDX_OUT_OF_RANGE
    )
