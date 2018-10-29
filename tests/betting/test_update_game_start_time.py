import pytest

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game
from scorum.utils.time import to_date, date_to_str
from tests.common import validate_response, check_virt_ops, DEFAULT_WITNESS


@pytest.mark.parametrize('time_shift', [30])
def test_update_game_start_time(wallet: Wallet, time_shift):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    uuid, _ = create_game(wallet, DEFAULT_WITNESS, start=30, delay=3600)
    game_before = wallet.get_games_by_uuids([uuid])[0]
    start_time = date_to_str(to_date(game_before['start_time'], tmdelta={'seconds': time_shift}))
    response = wallet.update_game_start_time(uuid, DEFAULT_WITNESS, start_time)
    validate_response(response, wallet.update_game_start_time.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["update_game_start_time"])
    game_after = wallet.get_games_by_uuids([uuid])[0]
    assert game_before['start_time'] != game_after['start_time']
    assert game_after['start_time'] == start_time
