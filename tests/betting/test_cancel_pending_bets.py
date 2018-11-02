import pytest
from scorum.graphenebase.betting import wincase, market

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game, post_bet
from tests.common import validate_response, DEFAULT_WITNESS, check_virt_ops


@pytest.mark.parametrize('better, market_type, wincase_type', [
    ('alice', market.RoundHome(), wincase.RoundHomeNo(), )
])
def test_cancel_pending_bets(wallet: Wallet, better, market_type, wincase_type):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    game_uuid, _ = create_game(wallet, DEFAULT_WITNESS, start=30, market_types=[market_type])
    bet_uuid, _ = post_bet(wallet, better, game_uuid, wincase=wincase_type)
    response = wallet.cancel_pending_bets([bet_uuid], better)
    validate_response(response, wallet.cancel_pending_bets.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["cancel_pending_bets"])
