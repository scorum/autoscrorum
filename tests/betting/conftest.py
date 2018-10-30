import pytest

from scorum.utils.time import fmt_time_from_now
from scorum.graphenebase.betting import game, market, wincase
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


def empower_betting_moderator(wallet, account=DEFAULT_WITNESS):
    wallet.development_committee_empower_betting_moderator(DEFAULT_WITNESS, account)
    proposals = wallet.list_proposals()
    wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"])


def create_game(wallet, account=DEFAULT_WITNESS, **kwargs):
    """
    'Additional_argument' default_value:
    ---
    'json_metadata' "{}"
    'start' 3
    'delay' 30
    'game_type' game.Soccer()
    'market_types' []
    """
    uuid = gen_uid()
    response = wallet.create_game(
        uuid, account,
        kwargs.get('json_metadata', "{}"),
        fmt_time_from_now(kwargs.get("start", 3)), kwargs.get("delay", 30),
        kwargs.get("game_type", game.Soccer()), kwargs.get("market_types", [])
    )
    return uuid, response['block_num']


def post_bet(wallet, better, game_uuid, **kwargs):
    """
    'Additional_argument' default_value:
    ---
    'wincase_type' wincase.RoundHomeYes()
    'sodds' [3, 2]
    'stake' "1.000000000 SCR"
    'live' True
    """
    uuid = gen_uid()
    response = wallet.post_bet(
        uuid, better, game_uuid,
        kwargs.get("wincase_type", wincase.RoundHomeYes()),
        kwargs.get("odds", [3, 2]),
        kwargs.get("stake", "1.000000000 SCR"),
        kwargs.get("live", True)
    )
    return uuid, response['block_num']
