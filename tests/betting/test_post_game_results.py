from automation.wallet import Wallet
from tests.betting.conftest import create_game_with_bets, change_resolve_delay
from scorum.graphenebase.betting import wincase
from tests.common import validate_response, DEFAULT_WITNESS, check_virt_ops


def test_post_game_results(wallet: Wallet, bets):
    game_uuid, _ = create_game_with_bets(wallet, bets, 1)
    response = wallet.post_game_results(
        game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)]
    )
    validate_response(response, wallet.post_game_results.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["post_game_results"])


def test_post_game_results_game_resolve(wallet: Wallet, bets):
    change_resolve_delay(wallet, 3)
    game_uuid, _ = create_game_with_bets(wallet, bets, 1)
    response = wallet.post_game_results(game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    check_virt_ops(wallet, response["block_num"], response["block_num"], ["game_status_changed"])
    games = wallet.get_games_by_uuids([game_uuid])
    assert games == []

