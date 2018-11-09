import pytest
from scorum.graphenebase.betting import game, market
from scorum.utils.time import fmt_time_from_now

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator
from tests.common import (
    validate_response, gen_uid, check_virt_ops, validate_error_response, RE_START_TIME, RE_NOT_MODERATOR,
    RE_OBJECT_EXIST, RE_MISSING_AUTHORITY
)


@pytest.mark.parametrize('game_type,market_types', [
    (game.Soccer(), [market.ResultHome()]),
    (game.Soccer(), [market.Total(1000), market.Handicap(-500), market.CorrectScore(5, 0)]),
    (game.Hockey(), [market.ResultHome(), market.GoalBoth()])
])
@pytest.mark.parametrize('moderator', ['alice'])
@pytest.mark.parametrize('start,delay', [(1, 30), (30, 60)])
def test_create_game(wallet_4hf: Wallet, game_type, market_types, moderator, start, delay):
    empower_betting_moderator(wallet_4hf, moderator)
    response = wallet_4hf.create_game(
        gen_uid(), moderator, "{}", fmt_time_from_now(start), delay, game_type, market_types)
    validate_response(response, wallet_4hf.create_game.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["create_game"])


@pytest.mark.parametrize('moderator,start,markets,expected_error', [
    ["alice", 0, [], RE_START_TIME],
    ["bob", 3, [], RE_NOT_MODERATOR],
    ["alice", 0, [market.RoundHome(), market.RoundHome()], "You provided duplicates in market list"],
    ["alice", 0, [market.Total()], "You've provided invalid market type"],
    ["alice", 0, [market.Handicap(-1200)], "You've provided invalid market type"],
    ["alice", 0, [market.TotalGoalsHome(650)], "You've provided invalid market type"],
])
def test_create_game_invalid_params(wallet_4hf: Wallet, moderator, start, markets, expected_error):
    empower_betting_moderator(wallet_4hf, "alice")
    response = wallet_4hf.create_game(
        gen_uid(), moderator, "{}", fmt_time_from_now(start), 30, game.Soccer(), markets)
    validate_error_response(response, wallet_4hf.create_game.__name__, expected_error)


def test_create_game_invalid_signing(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf, "alice")
    g = {
        "uuid": gen_uid(), "moderator": "alice", "start_time": fmt_time_from_now(3), "json_metadata": "{}",
        "auto_resolve_delay_sec": 30, "game": game.Soccer(), "markets": []
    }
    response = wallet_4hf.broadcast_multiple_ops("create_game", [g], ["bob"])
    validate_error_response(response, "create_game", RE_MISSING_AUTHORITY)


@pytest.mark.parametrize('moderator', ['alice'])
def test_create_game_same_uuid(wallet_4hf: Wallet, moderator):
    empower_betting_moderator(wallet_4hf, moderator)
    uuid = gen_uid()
    wallet_4hf.create_game(uuid, moderator, "{}", fmt_time_from_now(3), 30, game.Soccer(), [])
    response = wallet_4hf.create_game(uuid, moderator, "{}", fmt_time_from_now(3), 30, game.Soccer(), [])
    validate_error_response(response, wallet_4hf.create_game.__name__, RE_OBJECT_EXIST)


@pytest.mark.parametrize('moderator', ['alice'])
def test_create_game_same_after_cancel(wallet_4hf: Wallet, moderator):
    empower_betting_moderator(wallet_4hf, moderator)
    uuid = gen_uid()
    wallet_4hf.create_game(uuid, moderator, "{}", fmt_time_from_now(10), 30, game.Soccer(), [])
    wallet_4hf.cancel_game(uuid, moderator)
    response = wallet_4hf.create_game(uuid, moderator, "{}", fmt_time_from_now(10), 30, game.Soccer(), [])
    validate_error_response(response, wallet_4hf.create_game.__name__, RE_OBJECT_EXIST)
