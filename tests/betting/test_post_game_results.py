from automation.wallet import Wallet
from tests.betting.conftest import create_game_with_bets, change_resolve_delay
from scorum.graphenebase.betting import wincase
from tests.common import validate_response, DEFAULT_WITNESS, check_virt_ops


def test_post_game_results(wallet_4hf: Wallet, bets):
    game_uuid, _ = create_game_with_bets(wallet_4hf, bets, 1)
    response = wallet_4hf.post_game_results(
        game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)]
    )
    validate_response(response, wallet_4hf.post_game_results.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], response['block_num'], ["post_game_results"])


def test_post_game_results_game_resolve(wallet_4hf: Wallet, bets):
    change_resolve_delay(wallet_4hf, 3)
    game_uuid, _ = create_game_with_bets(wallet_4hf, bets, 1)
    response = wallet_4hf.post_game_results(game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    check_virt_ops(wallet_4hf, response["block_num"], response["block_num"], ["game_status_changed"])
    games = wallet_4hf.get_games_by_uuids([game_uuid])
    assert games == []

