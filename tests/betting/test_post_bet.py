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
def test_post_bet(wallet_4hf: Wallet, better, market_type, wincase_type, odds, stake, live):
    empower_betting_moderator(wallet_4hf, DEFAULT_WITNESS)
    balance_before = wallet_4hf.get_account_scr_balance(better)
    game_uuid, _ = create_game(wallet_4hf, DEFAULT_WITNESS, market_types=[market_type])
    bet_uuid = gen_uid()
    response = wallet_4hf.post_bet(bet_uuid, better, game_uuid, wincase_type, odds, stake, live)
    validate_response(response, wallet_4hf.post_bet.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], response['block_num'], ["post_bet"])
    balance_after = wallet_4hf.get_account_scr_balance(better)
    assert balance_before - Amount(stake) == balance_after


@pytest.mark.parametrize('market_type, wincase_type, odds, stake, live, expected_error', [
    (
        market.RoundHome(), wincase.HandicapOver(), [2, 1], "5.000000000 SCR", True,
        "Wincase .* dont belongs to game markets"
    ),
    (
        market.Handicap(100), wincase.HandicapOver(10), [2, 1], "5.000000000 SCR", True,
        "Wincase .* is invalid"
    ),
    (
        market.CorrectScore(3, 3), wincase.CorrectScoreYes(17, 23), [2, 1], "5.000000000 SCR", True,
        "Wincase .* is invalid"
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
def test_post_bet_invalid_params(wallet_4hf: Wallet, market_type, wincase_type, odds, stake, live, expected_error):
    empower_betting_moderator(wallet_4hf)
    game_uuid, _ = create_game(wallet_4hf, start=1, market_types=[market_type])
    response = wallet_4hf.post_bet(gen_uid(), "alice", game_uuid, wincase_type, odds, stake, live)
    validate_error_response(response, wallet_4hf.post_bet.__name__, expected_error)


def test_post_bet_same_uuid(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf)
    game_uuid, _ = create_game(wallet_4hf, start=1, market_types=[market.RoundHome()])
    bet_uuid, _ = post_bet(wallet_4hf, "alice", game_uuid, wincase=wincase.RoundHomeYes())
    wallet_4hf.cancel_pending_bets([bet_uuid], "alice")
    response = wallet_4hf.post_bet(bet_uuid, "alice", game_uuid, wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR", True)
    validate_error_response(response, wallet_4hf.post_bet.__name__, RE_OBJECT_EXIST)


def test_post_bet_same_uuid_few_games(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf)
    game1, _ = create_game(wallet_4hf, delay=3600, market_types=[market.RoundHome()])
    game2, _ = create_game(wallet_4hf, delay=3600, market_types=[market.RoundHome()])
    bet_uuid, _ = post_bet(wallet_4hf, "alice", game1, wincase=wincase.RoundHomeYes())
    response = wallet_4hf.post_bet(bet_uuid, "alice", game2, wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR", True)
    validate_error_response(response, wallet_4hf.post_bet.__name__, RE_OBJECT_EXIST)


def test_post_bet_auto_resolve(wallet_4hf: Wallet, bets):
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    game_uuid, bets_uuid = create_game_with_bets(wallet_4hf, bets, 1, 9)
    accounts_after = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    assert wallet_4hf.get_pending_bets(bets_uuid) == []
    assert wallet_4hf.get_matched_bets(bets_uuid) == []
    assert all(accounts_after[name]["balance"] == accounts_before[name]["balance"] for name in names), \
        "All accounts should receive back their stakes."


def test_post_bet_finished_game_resolve(wallet_4hf: Wallet, bets):
    change_resolve_delay(wallet_4hf, 3)  # resolve game next block after it will be finished
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    game_uuid, bets_uuid = create_game_with_bets(wallet_4hf, bets, 1)
    response = wallet_4hf.post_game_results(game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    wallet_4hf.get_block(response["block_num"], wait_for_block=True)
    accounts_after = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    assert wallet_4hf.get_pending_bets(bets_uuid) == []
    assert wallet_4hf.get_matched_bets(bets_uuid) == []
    # check rewards distribution
