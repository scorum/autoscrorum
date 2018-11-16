import pytest
from scorum.graphenebase.betting import wincase, market

from tests.common import validate_response, DEFAULT_WITNESS, check_virt_ops, validate_error_response


@pytest.mark.parametrize('better, start, market_type, wincase_type', [
    ('alice', 30, market.RoundHome(), wincase.RoundHomeNo()),
    ('alice', 1, market.RoundHome(), wincase.RoundHomeNo())
])
def test_cancel_pending_bets(wallet_4hf, betting, better, start, market_type, wincase_type):
    game_uuid, _ = betting.create_game(start=start, market_types=[market_type])
    bet_uuid, _ = betting.post_bet(better, game_uuid, wincase=wincase_type)
    response = wallet_4hf.cancel_pending_bets([bet_uuid], better)
    validate_response(response, wallet_4hf.cancel_pending_bets.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["cancel_pending_bets"])


@pytest.mark.parametrize('better, start, live, expected_error', [
    ('alice', 10, True, "Invalid better"),
    (DEFAULT_WITNESS, 5, False, "Bet .* doesn't exist")
])
def test_cancel_pending_bets_invalid_params(wallet_4hf, betting, better, start, live, expected_error):
    game_uuid, _ = betting.create_game(start=start, market_types=[market.RoundHome()])
    bet_uuid, block_num = betting.post_bet(DEFAULT_WITNESS, game_uuid, wincase=wincase.RoundHomeYes(), live=live)
    wallet_4hf.get_block(block_num + 1, wait_for_block=True)
    response = wallet_4hf.cancel_pending_bets([bet_uuid], better)
    validate_error_response(response, wallet_4hf.cancel_pending_bets.__name__, expected_error)


@pytest.mark.parametrize('better', ['alice'])
def test_cancel_pending_bet_same_bet(wallet_4hf, betting, better):
    game_uuid, _ = betting.create_game(start=30, market_types=[market.RoundHome()])
    bet_uuid, _ = betting.post_bet(better, game_uuid, wincase=wincase.RoundHomeYes())
    wallet_4hf.cancel_pending_bets([bet_uuid], better)
    response = wallet_4hf.cancel_pending_bets([bet_uuid], better)
    validate_error_response(response, wallet_4hf.cancel_pending_bets.__name__, "Bet .* doesn't exist")
