from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game
from scorum.graphenebase.betting import wincase
from tests.common import validate_response, DEFAULT_WITNESS, check_virt_ops


def test_post_game_results(wallet: Wallet):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    uuid, block_num = create_game(wallet, DEFAULT_WITNESS, start=3, delay=3600)
    response = wallet.post_game_results(uuid, DEFAULT_WITNESS, [wincase.ResultHomeYes()])
    validate_response(response, wallet.post_game_results.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["post_game_results"])
