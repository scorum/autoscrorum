import pytest
from scorum.graphenebase.betting import wincase, market

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game, post_bet
from tests.common import validate_response, DEFAULT_WITNESS, check_virt_ops


@pytest.mark.parametrize('better, market_type, wincase_type', [
    ('alice', market.RoundHome(), wincase.RoundHomeNo(), )
])
def test_cancel_pending_bets(wallet_4hf: Wallet, better, market_type, wincase_type):
    empower_betting_moderator(wallet_4hf, DEFAULT_WITNESS)
    game_uuid, _ = create_game(wallet_4hf, DEFAULT_WITNESS, start=30, market_types=[market_type])
    bet_uuid, _ = post_bet(wallet_4hf, better, game_uuid, wincase=wincase_type)
    response = wallet_4hf.cancel_pending_bets([bet_uuid], better)
    validate_response(response, wallet_4hf.cancel_pending_bets.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], response['block_num'], ["cancel_pending_bets"])
