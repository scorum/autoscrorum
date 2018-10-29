import pytest

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game
from scorum.graphenebase.betting import wincase
from tests.common import validate_response, DEFAULT_WITNESS, check_virt_ops, gen_uid


@pytest.mark.parametrize('better, wincase_type, odds, stake', [
    ('alice', wincase.RoundHomeNo(), [2, 1], "5.000000000 SCR")
])
def test_cancel_pending_bets(wallet: Wallet, better, wincase_type, odds, stake):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    game_uuid, _ = create_game(wallet, DEFAULT_WITNESS, start=3, delay=3600)
    bet_uuid = gen_uid()
    wallet.post_bet(bet_uuid, better, game_uuid, wincase_type, odds, stake, True)
    response = wallet.cancel_pending_bets([bet_uuid], better)
    validate_response(response, wallet.cancel_pending_bets.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["cancel_pending_bets"])
