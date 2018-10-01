import pytest
from src.wallet import Wallet
from tests.common import validate_response, validate_error_response, DEFAULT_WITNESS


@pytest.mark.parametrize('budget_type', ['post', 'banner'])
@pytest.mark.parametrize('coeffs', [[90, 50], [100, 80, 30, 25, 17, 1], [100, 100, 100]])  # 1-100, len 2-N, desc
def test_proposal_creation_and_vote(wallet_3hf: Wallet, budget_type, coeffs):
    response = wallet_3hf.development_committee_change_budgets_auction_properties(
        DEFAULT_WITNESS, coeffs, 86400, budget_type
    )
    validate_response(response, wallet_3hf.development_committee_change_budgets_auction_properties.__name__)
    proposals = wallet_3hf.list_proposals()
    validate_response(proposals, wallet_3hf.list_proposals.__name__)
    assert len(proposals) == 1, "Was created %d proposals, expected only one: %s" % (len(proposals), proposals)

    validate_response(wallet_3hf.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"]), wallet_3hf.proposal_vote.__name__)


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
