from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game
from tests.common import validate_response, check_virt_ops, DEFAULT_WITNESS


def test_cancel_game(wallet: Wallet):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    uuid, _ = create_game(wallet, DEFAULT_WITNESS, delay=3600)
    response = wallet.cancel_game(uuid, DEFAULT_WITNESS)
    validate_response(response, wallet.cancel_game.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["cancel_game"])
    assert wallet.get_games_by_uuids([uuid]) == [], "All games should be closed"
