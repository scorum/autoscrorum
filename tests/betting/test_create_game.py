from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator
from scorum.utils.time import fmt_time_from_now
from scorum.graphenebase.betting import game, market
from tests.common import validate_response


def test_create_game(wallet: Wallet):
    empower_betting_moderator(wallet, 'alice')
    validate_response(wallet.create_game(
        "e629f9aa-6b2c-46aa-8fa8-36770e7a7a5f",
        "alice",
        "game_name",
        fmt_time_from_now(10),
        33,
        game.Soccer(),
        [market.Total(1000)]
    ),
        wallet.create_game.__name__
    )
