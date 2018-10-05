import pytest

from src.wallet import Wallet
from tests.common import DEFAULT_WITNESS, RE_OP_IS_LOCKED, validate_error_response


"""
Advertising operations should be locked until 3rd hardfork.
"""


def test_create_budget_locked(wallet: Wallet, budget):
    response = wallet.create_budget(**budget)
    validate_error_response(response, wallet.create_budget.__name__, RE_OP_IS_LOCKED)


def test_close_budget_locked(wallet: Wallet, budget):
    response = wallet.close_budget(budget["type"], 0, DEFAULT_WITNESS)
    validate_error_response(response, wallet.close_budget.__name__, RE_OP_IS_LOCKED)


def test_update_budget_locked(wallet: Wallet, budget):
    response = wallet.update_budget(budget["type"], 0, DEFAULT_WITNESS, "{}")
    validate_error_response(response, wallet.close_budget.__name__, RE_OP_IS_LOCKED)


@pytest.mark.parametrize('moderator', ['alice', DEFAULT_WITNESS, 'bob'])
def test_empower_adv_moderator_locked(wallet: Wallet, budget, moderator):
    response = wallet.development_committee_empower_advertising_moderator(DEFAULT_WITNESS, moderator)
    validate_error_response(response, wallet.development_committee_empower_advertising_moderator, RE_OP_IS_LOCKED)


@pytest.mark.parametrize('moderator', ['alice', DEFAULT_WITNESS, 'bob'])
def test_close_budget_by_adv_moderator_locked(wallet: Wallet, budget, moderator):
    response = wallet.close_budget_by_advertising_moderator(moderator, 0, budget["type"])
    validate_error_response(response, wallet.close_budget_by_advertising_moderator.__name__, RE_OP_IS_LOCKED)


@pytest.mark.parametrize('budget_type', ['post', 'budget'])
def test_development_committee_change_budgets_auction_properties(wallet: Wallet, budget_type):
    response = wallet.development_committee_change_budgets_auction_properties(
        DEFAULT_WITNESS, [90, 50], budget_type=budget_type
    )
    validate_error_response(
        response, wallet.development_committee_change_budgets_auction_properties.__name__, RE_OP_IS_LOCKED
    )
