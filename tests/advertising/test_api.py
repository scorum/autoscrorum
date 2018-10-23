from copy import copy

import pytest
from scorum.graphenebase.amount import Amount

from automation.wallet import Wallet
from tests.advertising.conftest import empower_advertising_moderator, update_budget_balance, update_budget_time
from tests.common import (
    MAX_INT_64, RE_INVALID_UUID, validate_response, validate_error_response, gen_uid
)


@pytest.mark.parametrize('moderator', ['alice'])
def test_get_moderator(wallet_3hf: Wallet, moderator):
    assert wallet_3hf.get_moderator() is None, "Moderator shouldn't be set yet."
    empower_advertising_moderator(wallet_3hf, moderator)
    response = wallet_3hf.get_moderator()
    validate_response(response, wallet_3hf.get_moderator.__name__, [('name', moderator)])


def test_get_user_budgets(wallet_3hf: Wallet, opened_budgets_same_acc):
    owner = opened_budgets_same_acc[0]['owner']
    response = wallet_3hf.get_user_budgets(owner)
    validate_response(response, wallet_3hf.get_user_budgets.__name__)
    assert len(response) == len(opened_budgets_same_acc)
    assert all(b['owner'] == owner for b in response)
    assert wallet_3hf.get_user_budgets("unknown") == [], "There shouldn't be budgets for unknown user."


def test_get_user_budgets_post_vs_banner(wallet_3hf: Wallet, budgets):
    owner = budgets[0]['owner']
    for budget in budgets:
        update_budget_time(wallet_3hf, budget)
        wallet_3hf.create_budget(**budget)
        update_budget_balance(wallet_3hf, budget)
    response = wallet_3hf.get_user_budgets(owner)
    validate_response(response, wallet_3hf.get_user_budgets.__name__)
    assert len(response) == len(budgets)
    assert all(b['owner'] == owner for b in response)


def test_get_budget(wallet_3hf: Wallet, budget):
    update_budget_time(wallet_3hf, budget)
    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)
    budget_obj = wallet_3hf.get_budget(budget["uuid"], budget["type"])
    validate_response(
        budget_obj,  wallet_3hf.get_budget.__name__,
        [
            ('owner', budget['owner']), 'balance', 'per_block', 'owner_pending_income', 'budget_pending_outgo',
            'start', 'created', 'deadline', 'cashout_time', 'uuid'
        ]
    )


def test_get_budgets(wallet_3hf: Wallet, opened_budgets):
    budgets = wallet_3hf.get_budgets([b['owner'] for b in opened_budgets], opened_budgets[0]['type'])
    validate_response(budgets,  wallet_3hf.get_budget.__name__)
    assert len(budgets) == len(opened_budgets)


@pytest.mark.parametrize('uuid', [-1, MAX_INT_64, 'asd'])
def test_get_budget_invalid_uuid(wallet_3hf: Wallet, opened_budgets, uuid):
    budget = opened_budgets[0]
    validate_error_response(
        wallet_3hf.get_budget(uuid, budget["type"]), wallet_3hf.get_budget.__name__, RE_INVALID_UUID
    )


@pytest.mark.parametrize('uuid', [gen_uid])
def test_get_budget_unknown_uuid(wallet_3hf: Wallet, opened_budgets, uuid):
    budget = opened_budgets[0]
    assert wallet_3hf.get_budget(uuid(), budget["type"]) is None


@pytest.mark.parametrize('budget_type', ['post', 'banner'])
def test_get_auction_coefficients(wallet_3hf: Wallet, budget_type):
    response = wallet_3hf.get_auction_coefficients(budget_type)
    validate_response(response, wallet_3hf.get_auction_coefficients.__name__)
    cfg = wallet_3hf.get_config()
    # 'BOOST_PP_TUPLE_REM_CTOR_O_4({100, 85, 75, 65})' -> [100, 85, 75, 65]
    default_auction_coeffs = [
        int(c) for c in cfg["SCORUM_DEFAULT_BUDGETS_AUCTION_SET"].split('O_4')[1][2:-2].split(', ')
    ]
    assert response == default_auction_coeffs, "Default auction coefficient values are not correct."


def test_get_current_winners(wallet_3hf: Wallet, opened_budgets):
    budget_type = opened_budgets[0]["type"]
    response = wallet_3hf.get_current_winners(budget_type)
    validate_response(response, wallet_3hf.get_current_winners.__name__)
    assert len(response) == len(set([b['owner'] for b in opened_budgets]))


@pytest.mark.parametrize('order', [[5, 4, 3, 2, 1], [1, 2, 3, 4, 5], [3, 1, 5, 4, 2]])
def test_get_current_winners_order(wallet_3hf: Wallet, budget, order):
    coeffs = wallet_3hf.get_auction_coefficients(budget['type'])

    for i in order:
        b = copy(budget)
        update_budget_time(wallet_3hf, b)
        b.update({'balance': str(Amount(b['balance']) * (i / 10)), 'uuid': gen_uid()})
        wallet_3hf.create_budget(**b)

    response = wallet_3hf.get_current_winners(budget["type"])
    assert len(response) <= len(coeffs)
    assert all(response[i]['per_block'] > response[i + 1]['per_block'] for i in range(0, len(response) - 1)), \
        "Winners should be ordered by per_block value in descending order."
