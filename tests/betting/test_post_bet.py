import pytest
from scorum.graphenebase.amount import Amount
from scorum.graphenebase.betting import wincase, market

from automation.wallet import Wallet
from tests.betting.conftest import (
    empower_betting_moderator, create_game, post_bet, create_game_with_bets, change_resolve_delay
)
from tests.common import (
    validate_response, gen_uid, DEFAULT_WITNESS, check_virt_ops, validate_error_response, RE_OBJECT_EXIST
)


@pytest.mark.parametrize('better, market_type, wincase_type, odds, stake, live', [
    ('alice', market.RoundHome(), wincase.RoundHomeNo(), [2, 1], "5.000000000 SCR", True),
    ('bob', market.Handicap(-500), wincase.HandicapOver(-500), [3, 2], "3.000000000 SCR", True)
])
def test_post_bet(wallet: Wallet, better, market_type, wincase_type, odds, stake, live):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    balance_before = wallet.get_account_scr_balance(better)
    game_uuid, _ = create_game(wallet, DEFAULT_WITNESS, market_types=[market_type])
    bet_uuid = gen_uid()
    response = wallet.post_bet(bet_uuid, better, game_uuid, wincase_type, odds, stake, live)
    validate_response(response, wallet.post_bet.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["post_bet"])
    balance_after = wallet.get_account_scr_balance(better)
    assert balance_before - Amount(stake) == balance_after


@pytest.mark.parametrize('market_type, wincase_type, odds, stake, live, expected_error', [
    (
        market.RoundHome(), wincase.HandicapOver(), [2, 1], "5.000000000 SCR", True,
        "Wincase .* dont belongs to game markets"
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [2, 1], "5.000000000 SP", True,
        "Stake must be SCR"
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [2, 1], "-5.000000000 SCR", True,
        "Stake must be greater  or equal then"
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [-2, 1], "5.000000000 SCR", True,
        "odds numerator must be greater then zero"
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [2, -1], "5.000000000 SCR", True,
        "odds denominator must be greater then zero"
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [1, 2], "5.000000000 SCR", True,
        "odds must be greater then one"
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [2, 1], "5.000000000 SCR", False,
        "Cannot create non-live bet after game was started"
    ),
])
def test_post_bet_invalid_params(wallet: Wallet, market_type, wincase_type, odds, stake, live, expected_error):
    empower_betting_moderator(wallet)
    game_uuid, _ = create_game(wallet, start=1, market_types=[market_type])
    response = wallet.post_bet(gen_uid(), "alice", game_uuid, wincase_type, odds, stake, live)
    validate_error_response(response, wallet.post_bet.__name__, expected_error)


def test_post_bet_same_uuid(wallet: Wallet):
    empower_betting_moderator(wallet)
    game_uuid, _ = create_game(wallet, start=1, market_types=[market.RoundHome()])
    bet_uuid, _ = post_bet(wallet, "alice", game_uuid, wincase=wincase.RoundHomeYes())
    wallet.cancel_pending_bets([bet_uuid], "alice")
    response = wallet.post_bet(bet_uuid, "alice", game_uuid, wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR", True)
    validate_error_response(response, wallet.post_bet.__name__, RE_OBJECT_EXIST)


def test_post_bet_same_uuid_few_games(wallet: Wallet):
    empower_betting_moderator(wallet)
    game1, _ = create_game(wallet, delay=3600, market_types=[market.RoundHome()])
    game2, _ = create_game(wallet, delay=3600, market_types=[market.RoundHome()])
    bet_uuid, _ = post_bet(wallet, "alice", game1, wincase=wincase.RoundHomeYes())
    response = wallet.post_bet(bet_uuid, "alice", game2, wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR", True)
    validate_error_response(response, wallet.post_bet.__name__, RE_OBJECT_EXIST)


def test_post_bet_auto_resolve(wallet: Wallet, bets):
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet.get_accounts(names)}
    game_uuid, bets_uuid = create_game_with_bets(wallet, bets, 1, 9)
    accounts_after = {a["name"]: a for a in wallet.get_accounts(names)}
    assert wallet.get_pending_bets(bets_uuid) == []
    assert wallet.get_matched_bets(bets_uuid) == []
    assert all(accounts_after[name]["balance"] == accounts_before[name]["balance"] for name in names), \
        "All accounts should receive back their stakes."


def test_post_bet_finished_game_resolve(wallet: Wallet, bets):
    change_resolve_delay(wallet, 3)  # resolve game next block after it will be finished
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet.get_accounts(names)}
    game_uuid, bets_uuid = create_game_with_bets(wallet, bets, 1)
    response = wallet.post_game_results(game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    wallet.get_block(response["block_num"], wait_for_block=True)
    accounts_after = {a["name"]: a for a in wallet.get_accounts(names)}
    assert wallet.get_pending_bets(bets_uuid) == []
    assert wallet.get_matched_bets(bets_uuid) == []
    # check rewards distribution
