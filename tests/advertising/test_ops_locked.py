import pytest

from automation.wallet import Wallet
from tests.common import DEFAULT_WITNESS, RE_OP_IS_LOCKED, validate_error_response, gen_uid

"""
Advertising operations should be locked until 3rd hardfork.
"""


@pytest.mark.skip("Deprecated after 4th hardfork.")
def test_create_budget_locked(wallet: Wallet, budget):
    response = wallet.create_budget(**budget)
    validate_error_response(response, wallet.create_budget.__name__, RE_OP_IS_LOCKED)


@pytest.mark.skip("Deprecated after 4th hardfork.")
def test_close_budget_locked(wallet: Wallet, budget):
    response = wallet.close_budget(gen_uid(), DEFAULT_WITNESS, budget["type"])
    validate_error_response(response, wallet.close_budget.__name__, RE_OP_IS_LOCKED)


@pytest.mark.skip("Deprecated after 4th hardfork.")
def test_update_budget_locked(wallet: Wallet, budget):
    response = wallet.update_budget(gen_uid(), DEFAULT_WITNESS, "{}", budget["type"])
    validate_error_response(response, wallet.close_budget.__name__, RE_OP_IS_LOCKED)


@pytest.mark.skip("Deprecated after 4th hardfork.")
@pytest.mark.parametrize('moderator', ['alice', DEFAULT_WITNESS, 'bob'])
def test_empower_adv_moderator_locked(wallet: Wallet, budget, moderator):
    response = wallet.development_committee_empower_advertising_moderator(DEFAULT_WITNESS, moderator)
    validate_error_response(response, wallet.development_committee_empower_advertising_moderator, RE_OP_IS_LOCKED)


@pytest.mark.skip("Deprecated after 4th hardfork.")
@pytest.mark.parametrize('moderator', ['alice', DEFAULT_WITNESS, 'bob'])
def test_close_budget_by_adv_moderator_locked(wallet: Wallet, budget, moderator):
    response = wallet.close_budget_by_advertising_moderator(gen_uid(), moderator, budget["type"])
    validate_error_response(response, wallet.close_budget_by_advertising_moderator.__name__, RE_OP_IS_LOCKED)


@pytest.mark.skip("Deprecated after 4th hardfork.")
@pytest.mark.parametrize('type', ['post', 'budget'])
def test_development_committee_change_budgets_auction_properties(wallet: Wallet, type):
    response = wallet.development_committee_change_budgets_auction_properties(
        DEFAULT_WITNESS, [90, 50], type=type
    )
    validate_error_response(
        response, wallet.development_committee_change_budgets_auction_properties.__name__, RE_OP_IS_LOCKED
    )
