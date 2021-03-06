from copy import copy

import pytest
from scorum.graphenebase.amount import Amount

from automation.wallet import Wallet
from tests.advertising.conftest import update_budget_time, empower_advertising_moderator, update_budget_balance
from tests.common import (
    DEFAULT_WITNESS, validate_response, validate_error_response, RE_BUDGET_NOT_EXIST, check_virt_ops, gen_uid,
    RE_MISSING_AUTHORITY
)


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_before_starttime(wallet_3hf: Wallet, budget, moderator):
    update_budget_time(wallet_3hf, budget, start=30, deadline=60)  # to delay opening time for budget
    budget_balance = Amount(budget["balance"])
    balance_before = wallet_3hf.get_account_scr_balance(budget["owner"])

    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)  # update budget params / set budget id

    balance_after_create = wallet_3hf.get_account_scr_balance(budget["owner"])

    assert balance_before - balance_after_create == budget_balance

    empower_advertising_moderator(wallet_3hf, moderator)
    response = wallet_3hf.close_budget_by_advertising_moderator(budget["uuid"], moderator, budget["type"])
    validate_response(response, wallet_3hf.close_budget_by_advertising_moderator.__name__)

    balance_after_close = wallet_3hf.get_account_scr_balance(budget["owner"])
    assert balance_after_close == balance_after_create + budget_balance

    check_virt_ops(
        wallet_3hf, response['block_num'], response['block_num'],
        {'close_budget_by_advertising_moderator', 'budget_closing', 'budget_owner_income'}
    )
    assert len(wallet_3hf.get_budgets([budget['owner']], budget['type'])) == 0
    assert len(wallet_3hf.list_buddget_owners(budget_type=budget['type'])) == 0


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_after_starttime(wallet_3hf: Wallet, budget, moderator):
    update_budget_time(wallet_3hf, budget)
    budget_balance = Amount(budget["balance"])
    balance_before = wallet_3hf.get_account_scr_balance(budget["owner"])

    response = wallet_3hf.create_budget(**budget)
    create_block = response["block_num"]
    update_budget_balance(wallet_3hf, budget)  # update budget params / set budget id
    per_block = Amount(budget["per_block"])

    balance_after_create = wallet_3hf.get_account_scr_balance(budget["owner"])

    assert balance_before - balance_after_create == budget_balance

    empower_advertising_moderator(wallet_3hf, moderator)
    response = wallet_3hf.close_budget_by_advertising_moderator(budget["uuid"], moderator, budget["type"])
    validate_response(response, wallet_3hf.close_budget_by_advertising_moderator.__name__)
    close_block = response["block_num"]

    balance_after_close = wallet_3hf.get_account_scr_balance(budget["owner"])
    assert balance_after_close == balance_after_create + budget_balance - per_block * (close_block - create_block)

    check_virt_ops(
        wallet_3hf, close_block, close_block,
        {
            'close_budget_by_advertising_moderator', 'budget_closing', 'budget_owner_income',
            'budget_outgo'
        }
    )
    assert len(wallet_3hf.get_budgets([budget['owner']], budget['type'])) == 0
    assert len(wallet_3hf.list_buddget_owners(budget_type=budget['type'])) == 0


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_post_vs_banner(wallet_3hf: Wallet, moderator, post_budget, banner_budget):
    new_budget = copy(post_budget)
    update_budget_time(wallet_3hf, post_budget)
    wallet_3hf.create_budget(**post_budget)
    update_budget_balance(wallet_3hf, post_budget)  # update budget params / set budget id

    update_budget_time(wallet_3hf, banner_budget)
    wallet_3hf.create_budget(**banner_budget)
    update_budget_balance(wallet_3hf, banner_budget)  # update budget params / set budget id

    assert post_budget["id"] == banner_budget["id"]  # both = 0

    empower_advertising_moderator(wallet_3hf, moderator)
    response = wallet_3hf.close_budget_by_advertising_moderator(post_budget["uuid"], moderator, post_budget["type"])
    validate_response(response, wallet_3hf.close_budget_by_advertising_moderator.__name__)

    post_budgets = wallet_3hf.get_budgets([post_budget['owner']], post_budget['type'])
    assert len(post_budgets) == 0
    banner_budgets = wallet_3hf.get_budgets([banner_budget['owner']], banner_budget['type'])
    assert len(banner_budgets) == 1

    update_budget_time(wallet_3hf, new_budget)
    new_budget.update({'uuid': gen_uid()})
    validate_response(wallet_3hf.create_budget(**new_budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, new_budget)  # update budget params / set budget id
    assert new_budget["id"] > banner_budget["id"], "Newly created budget should have incremented index"


@pytest.mark.parametrize('moderator', ['alice', 'bob', DEFAULT_WITNESS])
def test_close_budgets(wallet_3hf: Wallet, moderator, opened_budgets_same_acc):
    budgets = opened_budgets_same_acc  # just renaming
    empower_advertising_moderator(wallet_3hf, moderator)
    validate_response(
        wallet_3hf.close_budget_by_advertising_moderator(budgets[0]["uuid"], moderator, budgets[0]["type"]),
        wallet_3hf.close_budget_by_advertising_moderator.__name__
    )

    rest_budgets = wallet_3hf.get_budgets([budgets[-1]["owner"]], budgets[-1]["type"])
    assert len(rest_budgets) == len(budgets) - 1
    assert all(rb["id"] != budgets[0]["id"] for rb in rest_budgets)
    # delete already deleted
    validate_error_response(
        wallet_3hf.close_budget_by_advertising_moderator(budgets[0]["uuid"], moderator, budgets[0]["type"]),
        wallet_3hf.close_budget_by_advertising_moderator.__name__,
        RE_BUDGET_NOT_EXIST
    )


@pytest.mark.parametrize('uuid', [gen_uid])
@pytest.mark.parametrize('moderator', ['alice'])
def test_unknown_uuid(wallet_3hf: Wallet, opened_budgets, uuid, moderator):
    empower_advertising_moderator(wallet_3hf, moderator)
    validate_error_response(
        wallet_3hf.close_budget_by_advertising_moderator(uuid(), moderator, opened_budgets[0]["type"]),
        wallet_3hf.close_budget_by_advertising_moderator.__name__,
        RE_BUDGET_NOT_EXIST
    )


@pytest.mark.parametrize('account', ['alice', DEFAULT_WITNESS, 'test.test2'])
def test_invalid_signing(wallet_3hf: Wallet, budget, account):
    update_budget_time(wallet_3hf, budget)
    data = {'uuid': budget['uuid'], 'moderator': budget['owner'], 'type': budget['type']}
    validate_error_response(
        wallet_3hf.broadcast_multiple_ops('close_budget_by_advertising_moderator', [data], {account}),
        'close_budget_by_advertising_moderator',
        RE_MISSING_AUTHORITY
    )
