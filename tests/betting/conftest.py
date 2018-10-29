import pytest

from scorum.utils.time import fmt_time_from_now
from scorum.graphenebase.betting import game, market
from tests.common import apply_hardfork, DEFAULT_WITNESS, gen_uid


GAME_FILTERS = [
    "created",
    "started",
    "finished",
    "resolved",
    "expired",
    "cancelled"
]


@pytest.fixture(scope="function")
def wallet_4hf(wallet):
    apply_hardfork(wallet, 4)
    return wallet


def empower_betting_moderator(wallet, account):
    wallet.development_committee_empower_betting_moderator(DEFAULT_WITNESS, account)
    proposals = wallet.list_proposals()
    wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"])


def create_game(wallet, account, **kwargs):
    """
    'Additional_argument' default_value:
    ---
    'postfix' ""
    'start' 3
    'delay' 30
    'game_type' game.Soccer()
    'market_types' []
    """
    uuid = gen_uid()
    game_name = "{}{}{}".format(account, "_test_game", kwargs.get("postfix", ""))
    response = wallet.create_game(
        uuid, account, game_name,
        fmt_time_from_now(kwargs.get("start", 3)), kwargs.get("delay", 30),
        kwargs.get("game_type", game.Soccer()), kwargs.get("market_types", [])
    )
    return uuid, response['block_num']
