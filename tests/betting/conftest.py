import pytest

from tests.common import apply_hardfork, DEFAULT_WITNESS


GAME_FILTERS = [
    "created",
    "started",
    "finished",
    "not_finished",
    "not_started",
    "not_created",
    "all"
]


@pytest.fixture(scope="function")
def wallet_4hf(wallet):
    apply_hardfork(wallet, 4)
    return wallet


def empower_betting_moderator(wallet, account):
    wallet.development_committee_empower_betting_moderator(DEFAULT_WITNESS, account)
    proposals = wallet.list_proposals()
    wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"])
