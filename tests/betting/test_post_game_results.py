import pytest

from tests.betting.betting import Bet
from scorum.graphenebase.betting import wincase, market
from tests.common import (
    validate_response, DEFAULT_WITNESS, check_virt_ops, validate_error_response, RE_NOT_MODERATOR
)


def test_post_game_results(wallet_4hf, betting, bets):
    game_uuid = betting.create_game_with_bets(bets, game_start=1)
    response = wallet_4hf.post_game_results(
        game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)]
    )
    validate_response(response, wallet_4hf.post_game_results.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["post_game_results"])


def test_post_game_results_game_resolve(wallet_4hf, betting, bets):
    betting.change_resolve_delay(3)
    game_uuid = betting.create_game_with_bets(bets, game_start=1)
    response = wallet_4hf.post_game_results(
        game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)]
    )
    check_virt_ops(wallet_4hf, response["block_num"], expected_ops=["game_status_changed"])
    games = wallet_4hf.get_games_by_uuids([game_uuid])
    assert games == []


@pytest.mark.parametrize('moderator, start, wincases, expected_error', [
    (DEFAULT_WITNESS, 1, [wincase.RoundHomeYes(), wincase.HandicapOver(10)], "Wincase .* is invalid"),
    ('alice', 1, [wincase.RoundHomeYes(), wincase.HandicapOver(500)], RE_NOT_MODERATOR),
    (DEFAULT_WITNESS, 30, [wincase.RoundHomeYes(), wincase.HandicapOver(500)], "The game is not started yet"),
    (DEFAULT_WITNESS, 1, [wincase.TotalOver(1000)], "Wincase .* doesn\'t belong to game markets"),
    (
        DEFAULT_WITNESS, 1, [wincase.RoundHomeYes(), wincase.RoundHomeNo()],
        "Wincase winners list do not contain neither .* nor"
    ),
    (DEFAULT_WITNESS, 1, [wincase.RoundHomeYes()], "Wincase winners list do not contain neither .* nor")
])
def test_post_game_results_invalid_params(wallet_4hf, betting, bets, start, wincases, moderator, expected_error):
    game_uuid = betting.create_game_with_bets(bets, game_start=start)
    response = wallet_4hf.post_game_results(game_uuid, moderator, wincases)
    validate_error_response(response, wallet_4hf.post_game_results.__name__, expected_error)


@pytest.mark.parametrize('bets, markets', [
    (
        [Bet('alice', wincase.TotalOver(1000), [2, 1])],
        [market.Total(1000)]
    ),
    (
        [Bet('alice', wincase.TotalOver(5000), [2, 1]), Bet('bob', wincase.TotalUnder(5000), [2, 1])],
        [market.Total(5000)]
    ),
    (
        [Bet('alice', wincase.HandicapOver(5000), [3, 1]), Bet('bob', wincase.HandicapUnder(5000), [3, 2])],
        [market.Handicap(5000)]
    ),
])
def test_post_game_payback_case(wallet_4hf, betting, markets, bets):
    betting.change_resolve_delay(3)
    names = [b.account for b in bets]
    balances_before = wallet_4hf.get_accounts_balances(names)
    game_uuid = betting.create_game_with_bets(bets, market_types=markets, game_start=1)
    response = wallet_4hf.post_game_results(game_uuid, DEFAULT_WITNESS, [])
    validate_response(response, wallet_4hf.post_game_results.__name__)
    balances_after = wallet_4hf.get_accounts_balances(names)
    assert all(balances_after[name] == balances_before[name] for name in names), \
        "All accounts should receive back their stakes."
