import pytest

from automation.wallet import Wallet
from tests.common import DEFAULT_WITNESS, validate_response


@pytest.mark.parametrize('moderator', ['alice'])
def test_devcommittee_empower_betting_moderator(wallet_4hf: Wallet, moderator):
    validate_response(wallet_4hf.development_committee_empower_betting_moderator(
        DEFAULT_WITNESS, moderator
    ), wallet_4hf.development_committee_empower_betting_moderator.__name__)
    proposals = wallet_4hf.list_proposals()
    assert len(proposals) == 1
    validate_response(wallet_4hf.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"]), wallet_4hf.proposal_vote.__name__)
    assert wallet_4hf.get_betting_properties()['moderator'] == moderator


@pytest.mark.parametrize('moderator1,moderator2', [('alice', 'bob')])
def test_devcommittee_empower_second_betting_moderator(wallet_4hf: Wallet, moderator1, moderator2):
    wallet_4hf.development_committee_empower_betting_moderator(DEFAULT_WITNESS, moderator1)
    wallet_4hf.proposal_vote(DEFAULT_WITNESS, 0)
    wallet_4hf.development_committee_empower_betting_moderator(DEFAULT_WITNESS, moderator2)
    wallet_4hf.proposal_vote(DEFAULT_WITNESS, 1)
    active_moderator = wallet_4hf.get_betting_properties()['moderator']
    assert active_moderator == moderator2
    assert active_moderator != moderator1
