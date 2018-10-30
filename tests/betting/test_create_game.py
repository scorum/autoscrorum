import pytest

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator
from scorum.utils.time import fmt_time_from_now
from scorum.graphenebase.betting import game, market
from tests.common import (
    validate_response, gen_uid, check_virt_ops, validate_error_response, RE_START_TIME, RE_NOT_MODERATOR
)


@pytest.mark.parametrize('game_type', [game.Soccer()])
@pytest.mark.parametrize('market_types', [
    [market.ResultHome()],
    [market.Total(1000), market.Handicap(-500), market.CorrectScore(5, 0)]
])
@pytest.mark.parametrize('moderator', ['alice'])
@pytest.mark.parametrize('start,delay', [(1, 30), (30, 60)])
def test_create_game(wallet: Wallet, game_type, market_types, moderator, start, delay):
    empower_betting_moderator(wallet, moderator)
    response = wallet.create_game(
        gen_uid(), moderator, "{}", fmt_time_from_now(start), delay, game_type, market_types)
    validate_response(response, wallet.create_game.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["create_game"])


@pytest.mark.parametrize('moderator,start,expected_error', [
    ["alice", 0, RE_START_TIME],
    ["bob", 3, RE_NOT_MODERATOR]
])
def test_create_game_invalid_params(wallet: Wallet, moderator, start, expected_error):
    empower_betting_moderator(wallet, "alice")
    response = wallet.create_game(
        gen_uid(), moderator, "{}", fmt_time_from_now(start), 30, game.Soccer(), [market.RoundHome()])
    validate_error_response(response, wallet.create_game.__name__, expected_error)
