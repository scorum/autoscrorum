import pytest
from scorum.utils.time import to_date, date_to_str, fmt_time_from_now
from scorum.graphenebase.betting import wincase
from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game
from tests.common import (
    validate_response, check_virt_ops, DEFAULT_WITNESS, validate_error_response, gen_uid,
    RE_OBJECT_NOT_EXIST, RE_NOT_MODERATOR, RE_MISSING_AUTHORITY, RE_START_TIME
)


@pytest.mark.parametrize('start,time_shift', [
    (30, 30),  # shift forward
    (30, -10)  # shift backward
])
def test_update_game_start_time(wallet: Wallet, start, time_shift):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    uuid, _ = create_game(wallet, DEFAULT_WITNESS, start=start, delay=3600)
    game_before = wallet.get_games_by_uuids([uuid])[0]
    start_time = date_to_str(to_date(game_before['start_time'], tmdelta={'seconds': time_shift}))
    response = wallet.update_game_start_time(uuid, DEFAULT_WITNESS, start_time)
    validate_response(response, wallet.update_game_start_time.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["update_game_start_time"])
    game_after = wallet.get_games_by_uuids([uuid])[0]
    assert game_before['start_time'] != game_after['start_time']
    assert game_after['start_time'] == start_time


@pytest.mark.parametrize('start,shift,expected_error', [
    (10, -30, RE_START_TIME),  # created game
    (1, -30, RE_START_TIME),  # started game
    (10, 44000, "Cannot change start time more than .* seconds")
])
def test_update_game_start_time_invalid_time(wallet: Wallet, start, shift, expected_error):
    empower_betting_moderator(wallet)
    uuid, _ = create_game(wallet, start=start)
    response = wallet.update_game_start_time(uuid, DEFAULT_WITNESS, fmt_time_from_now(shift))
    validate_error_response(response, wallet.update_game_start_time.__name__, expected_error)


def test_update_finished_game_start_time(wallet: Wallet):
    empower_betting_moderator(wallet)
    uuid, _ = create_game(wallet, start=1)
    wallet.post_game_results(uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes()])
    response = wallet.update_game_start_time(uuid, DEFAULT_WITNESS, fmt_time_from_now(30))
    validate_error_response(
        response, wallet.update_game_start_time.__name__, "Cannot change the start time when game is finished"
    )


def test_update_game_start_time_invalid_uuid(wallet: Wallet):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    response = wallet.update_game_start_time(gen_uid(), DEFAULT_WITNESS, fmt_time_from_now(30))
    validate_error_response(response, wallet.update_game_start_time.__name__, RE_OBJECT_NOT_EXIST)


def test_update_game_start_time_not_moderator(wallet: Wallet):
    empower_betting_moderator(wallet, "alice")
    uuid, _ = create_game(wallet, "alice")
    response = wallet.update_game_start_time(uuid, "bob", fmt_time_from_now(30))
    validate_error_response(response, wallet.update_game_start_time.__name__, RE_NOT_MODERATOR)


def test_update_game_start_time_invalid_signing(wallet: Wallet):
    empower_betting_moderator(wallet, "alice")
    uuid, _ = create_game(wallet, "alice")
    g = {"uuid": uuid, "moderator": "alice", "start_time": fmt_time_from_now(30)}
    response = wallet.broadcast_multiple_ops("update_game_start_time", [g], ["bob"])
    validate_error_response(response, "update_game_start_time", RE_MISSING_AUTHORITY)
