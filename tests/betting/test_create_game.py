from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator
from scorum.utils.time import fmt_time_from_now
from scorum.graphenebase.betting import game, market
from tests.common import validate_response, gen_uid, check_virt_ops


def test_create_game(wallet: Wallet):
    empower_betting_moderator(wallet, 'alice')
    response = wallet.create_game(
        gen_uid(), "alice", "game_name", fmt_time_from_now(10), 33, game.Soccer(), [market.Total(1000)])
    validate_response(response, wallet.create_game.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["create_game"])
