import pytest

from automation.wallet import Wallet
from tests.common import DEFAULT_WITNESS, validate_response


@pytest.mark.parametrize('moderator', ['alice'])
def test_devcommittee_empower_betting_moderator(wallet: Wallet, moderator):
    validate_response(wallet.development_committee_empower_betting_moderator(
        DEFAULT_WITNESS, moderator
    ), wallet.development_committee_empower_betting_moderator.__name__)
    proposals = wallet.list_proposals()
    assert len(proposals) == 1
    validate_response(wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"]), wallet.proposal_vote.__name__)
    assert wallet.get_betting_properties()['moderator'] == moderator
