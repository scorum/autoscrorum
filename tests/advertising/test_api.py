import pytest
from copy import copy
from src.wallet import Wallet
from graphenebase.amount import Amount
from tests.advertising.conftest import empower_advertising_moderator, update_budget_balance, update_budget_time
from tests.common import validate_response, DEFAULT_WITNESS, MAX_INT_64


@pytest.mark.parametrize('moderator', ['alice', 'bob', DEFAULT_WITNESS])
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
        update_budget_time(budget)
        validate_response(wallet_3hf.create_budget(**budget), wallet_3hf.create_budget.__name__)
        update_budget_balance(wallet_3hf, budget)
    response = wallet_3hf.get_user_budgets(owner)
    validate_response(response, wallet_3hf.get_user_budgets.__name__)
    assert len(response) == len(budgets)
    assert all(b['owner'] == owner for b in response)


def test_get_budget(wallet_3hf: Wallet, budget):
    update_budget_time(budget)
    validate_response(wallet_3hf.create_budget(**budget), wallet_3hf.create_budget.__name__)
    update_budget_balance(wallet_3hf, budget)
    budget_obj = wallet_3hf.get_budget(budget["id"], budget["type"])
    validate_response(
        budget_obj,  wallet_3hf.get_budget.__name__,
        [
            ('owner', budget['owner']), 'balance', 'per_block', 'owner_pending_income', 'budget_pending_outgo',
            'start', 'created', 'deadline', 'cashout_time'
        ]
    )


@pytest.mark.parametrize('idx', [-1, MAX_INT_64])
def test_get_budget_invalid_idx(wallet_3hf: Wallet, opened_budgets, idx):
    budget = opened_budgets[0]
    assert wallet_3hf.get_budget(idx, budget["type"]) is None


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
        update_budget_time(b)
        b['balance'] = str(Amount(b['balance']) * (i / 10))
        validate_response(wallet_3hf.create_budget(**b), wallet_3hf.create_budget.__name__)

    response = wallet_3hf.get_current_winners(budget["type"])
    validate_response(response, wallet_3hf.get_current_winners.__name__)
    assert len(response) <= len(coeffs)
    assert all(response[i]['per_block'] > response[i + 1]['per_block'] for i in range(0, len(response) - 1)), \
        "Winners should be ordered by per_block value in descending order."
