import pytest

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game
from scorum.graphenebase.betting import wincase
from scorum.graphenebase.amount import Amount
from tests.common import validate_response, gen_uid, DEFAULT_WITNESS, check_virt_ops


@pytest.mark.parametrize('better, wincase_type, odds, stake', [
    ('alice', wincase.RoundHomeNo(), [2, 1], "5.000000000 SCR"),
    ('bob', wincase.HandicapOver(-500), [3, 2], "3.000000000 SCR")
])
def test_post_bet(wallet: Wallet, better, wincase_type, odds, stake):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    balance_before = wallet.get_account_scr_balance(better)
    game_uuid, _ = create_game(wallet, DEFAULT_WITNESS)
    bet_uuid = gen_uid()
    response = wallet.post_bet(bet_uuid, better, game_uuid, wincase_type, odds, stake, True)
    validate_response(response, wallet.post_bet.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["post_bet"])
    balance_after = wallet.get_account_scr_balance(better)
    assert balance_before - Amount(stake) == balance_after
