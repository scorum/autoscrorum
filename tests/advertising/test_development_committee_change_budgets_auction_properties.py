import pytest
from src.wallet import Wallet
from tests.common import validate_response, validate_error_response, DEFAULT_WITNESS


def change_auction_coeffs(wallet, coeffs, budget_type):
    response = wallet.development_committee_change_budgets_auction_properties(
        DEFAULT_WITNESS, coeffs, 86400, budget_type
    )
    validate_response(response, wallet.development_committee_change_budgets_auction_properties.__name__)
    proposals = wallet.list_proposals()
    validate_response(proposals, wallet.list_proposals.__name__)
    assert len(proposals) == 1, "Was created %d proposals, expected only one: %s" % (len(proposals), proposals)
    validate_response(wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"]), wallet.proposal_vote.__name__)


@pytest.mark.parametrize('budget_type', ['post', 'banner'])
@pytest.mark.parametrize('coeffs', [[90, 50], [100, 80, 30, 25, 17, 1], [100, 100, 100]])  # 1-100, len 2-N, desc
def test_proposal_creation_and_vote(wallet_3hf: Wallet, budget_type, coeffs):
    change_auction_coeffs(wallet_3hf, coeffs, budget_type)
    assert coeffs == wallet_3hf.get_auction_coefficients(budget_type), "Coefficients wasn't set properly."


@pytest.mark.parametrize('budget_type', ['post', 'banner'])
@pytest.mark.parametrize('coeffs', [[], [105, 90], [50], [100, 0], [1, 50, 90]])  # 1-100, len 2-N, desc
def test_invalid_coeffs(wallet_3hf: Wallet, budget_type, coeffs):
    response = wallet_3hf.development_committee_change_budgets_auction_properties(
        DEFAULT_WITNESS, coeffs, 86400, budget_type
    )
    validate_error_response(response, wallet_3hf.development_committee_change_budgets_auction_properties.__name__)
    proposals = wallet_3hf.list_proposals()
    validate_response(proposals, wallet_3hf.list_proposals.__name__)
    assert len(proposals) == 0, "Was created %d proposals, expected only one: %s" % (len(proposals), proposals)
    assert coeffs != wallet_3hf.get_auction_coefficients(budget_type), "Coefficients was changed, but they shouldn't."


def test_coeffs_change(wallet_3hf, opened_budgets):
    budget_type = opened_budgets[0]['type']
    winners_before = wallet_3hf.get_current_winners(budget_type)
    assert len(winners_before) == len(opened_budgets)
    coeffs = wallet_3hf.get_auction_coefficients(budget_type)
    while len(coeffs) >= len(opened_budgets):
        coeffs = coeffs[1:]

    change_auction_coeffs(wallet_3hf, coeffs, budget_type)

    winners_after = wallet_3hf.get_current_winners(budget_type)
    assert len(winners_after) == len(coeffs)
    assert all(winners_after[i]['id'] == winners_before[i]['id'] for i in range(0, len(winners_after) - 1)), \
        "Should remain top '%d' winners before coeffs was changed." % len(coeffs)