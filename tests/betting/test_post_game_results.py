import pytest

from automation.wallet import Wallet
from tests.betting.conftest import create_game_with_bets, change_resolve_delay
from scorum.graphenebase.betting import wincase
from tests.common import (
    validate_response, DEFAULT_WITNESS, check_virt_ops, validate_error_response, RE_NOT_MODERATOR
)


def test_post_game_results(wallet_4hf: Wallet, bets):
    game_uuid = create_game_with_bets(wallet_4hf, bets, 1)
    response = wallet_4hf.post_game_results(
        game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)]
    )
    validate_response(response, wallet_4hf.post_game_results.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["post_game_results"])


def test_post_game_results_game_resolve(wallet_4hf: Wallet, bets):
    change_resolve_delay(wallet_4hf, 3)
    game_uuid = create_game_with_bets(wallet_4hf, bets, 1)
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
def test_post_game_results_invalid_params(wallet_4hf: Wallet, bets, start, wincases, moderator, expected_error):
    game_uuid = create_game_with_bets(wallet_4hf, bets, start)
    response = wallet_4hf.post_game_results(game_uuid, moderator, wincases)
    validate_error_response(response, wallet_4hf.post_game_results.__name__, expected_error)
