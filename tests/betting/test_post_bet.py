import pytest
from scorum.graphenebase.amount import Amount
from scorum.graphenebase.betting import wincase, market

from automation.wallet import Wallet
from tests.betting.conftest import (
    empower_betting_moderator, create_game, post_bet, create_game_with_bets, change_resolve_delay, Bet
)
from tests.common import (
    validate_response, gen_uid, DEFAULT_WITNESS, check_virt_ops, validate_error_response, RE_OBJECT_EXIST
)


ODDS_MAX = [1001, 1]
ODDS_MIN = [1001, 1000]
STAKE_MIN = "0.001000000 SCR"


@pytest.mark.parametrize('better, market_type, wincase_type, odds, stake, live', [
    ('alice', market.RoundHome(), wincase.RoundHomeNo(), [2, 1], "5.000000000 SCR", True),
    ('alice', market.CorrectScore(1, 1), wincase.CorrectScoreYes(1, 1), [2, 1], STAKE_MIN, True),
    ('alice', market.CorrectScoreAway(), wincase.CorrectScoreAwayNo(), ODDS_MIN, "5.000000000 SCR", True),
    ('bob', market.Total(1000), wincase.TotalOver(1000), ODDS_MAX, "1.000000000 SCR", True),
    ('bob', market.Handicap(-500), wincase.HandicapOver(-500), [3, 2], "3.000000000 SCR", True)
])
def test_post_bet(wallet_4hf: Wallet, better, market_type, wincase_type, odds, stake, live):
    empower_betting_moderator(wallet_4hf, DEFAULT_WITNESS)
    balance_before = wallet_4hf.get_account_scr_balance(better)
    game_uuid, _ = create_game(wallet_4hf, DEFAULT_WITNESS, market_types=[market_type])
    bet_uuid = gen_uid()
    response = wallet_4hf.post_bet(bet_uuid, better, game_uuid, wincase_type, odds, stake, live)
    validate_response(response, wallet_4hf.post_bet.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["post_bet"])
    balance_after = wallet_4hf.get_account_scr_balance(better)
    assert balance_before - Amount(stake) == balance_after


@pytest.mark.parametrize('market_type, wincase_type, odds, stake, live, expected_error', [
    (
        market.RoundHome(), wincase.HandicapOver(), [2, 1], "5.000000000 SCR", True,
        "Wincase .* doesn\'t belong to game markets"
    ),
    (
        market.Handicap(1000), wincase.HandicapOver(500), [2, 1], "5.000000000 SCR", True,
        "Wincase .* doesn\'t belong to game markets"
    ),
    (
        market.CorrectScore(3, 3), wincase.CorrectScoreYes(17, 23), [2, 1], "5.000000000 SCR", True,
        "Wincase .* doesn\'t belong to game markets"
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [2, 1], "5.000000000 SP", True,
        "Stake must be SCR"
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [2, 1], str(Amount(STAKE_MIN) - 1), True,
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
    (
        market.RoundHome(), wincase.RoundHomeYes(), [1002, 1], "5.000000000 SCR", False,
        "Invalid odds value"  # > MAX_ODDS
    ),
    (
        market.RoundHome(), wincase.RoundHomeYes(), [10009, 10000], "5.000000000 SCR", False,
        "Invalid odds value"  # < MIN_ODDS
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
    response = wallet_4hf.post_bet(
        bet_uuid, "alice", game_uuid, wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR", True)
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
    create_game_with_bets(wallet_4hf, bets, 1, 9)
    block = max(b.block_creation_num for b in bets)
    wallet_4hf.get_block(block + 1, wait_for_block=True)
    accounts_after = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    assert wallet_4hf.get_pending_bets([b.uuid for b in bets]) == []
    assert wallet_4hf.get_matched_bets([b.uuid for b in bets]) == []
    assert all(accounts_after[name]["balance"] == accounts_before[name]["balance"] for name in names), \
        "All accounts should receive back their stakes."


def test_post_bet_finished_game_resolve(wallet_4hf: Wallet, bets):
    change_resolve_delay(wallet_4hf, 3)  # resolve game next block after it will be finished
    game_uuid = create_game_with_bets(wallet_4hf, bets, 1)
    matched_bets = wallet_4hf.lookup_matched_bets(-1, 100)
    response = wallet_4hf.post_game_results(
        game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    wallet_4hf.get_block(response["block_num"], wait_for_block=True)
    if matched_bets:
        check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["bet_resolved"])
    assert wallet_4hf.get_pending_bets([b.uuid for b in bets]) == []
    assert wallet_4hf.get_matched_bets([b.uuid for b in bets]) == []


@pytest.mark.parametrize('bets, full_match', [
    ([
        Bet("alice", wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR"),
        Bet("bob", wincase.RoundHomeNo(), [3, 1], "1.000000000 SCR")
    ], False),
    ([
        Bet("alice", wincase.RoundHomeYes(), [2, 1], "1.000000000 SCR"),
        Bet("bob", wincase.RoundHomeNo(), [2, 1], "5.000000000 SCR")
    ], False),
    ([
        Bet("alice", wincase.RoundHomeYes(), [2, 1], "1.000000000 SCR"),
        Bet("bob", wincase.RoundHomeNo(), [2, 1], "1.000000000 SCR")
    ], True),
    ([
        Bet("alice", wincase.RoundHomeYes(), [3, 2], "0.000000013 SCR"),
        Bet("bob", wincase.RoundHomeNo(), [3, 1], "0.000000013 SCR")
    ], False),
    # ([
    #     Bet("alice", wincase.RoundHomeYes(), [999999, 998999], "0.000000013 SCR"),
    #     Bet("bob", wincase.RoundHomeNo(), [999999, 1000], "1.000000000 SCR")
    # ], False),
    # ([
    #     Bet("boss", wincase.RoundHomeNo(), [999999, 1000], "9500000.000000000 SCR"),
    #     Bet("alice", wincase.RoundHomeYes(), [999999, 998999], "1.000000000 SCR"),
    # ], False)
])
def test_bets_matching(wallet_4hf: Wallet, bets, full_match):
    empower_betting_moderator(wallet_4hf)
    create_game_with_bets(wallet_4hf, bets, game_start=1)
    block = max(b.block_creation_num for b in bets)
    check_virt_ops(wallet_4hf, block, expected_ops=["bets_matched", "bet_cancelled", "bet_updated"])
    pending_bets = wallet_4hf.lookup_pending_bets(-1, 100)
    if full_match:
        assert len(pending_bets) == 0, "There shouldn't be pending bets."
    else:
        assert len(pending_bets) == 1, "There should be left removed from pending bets"
        assert pending_bets[0]["data"]["stake"] == str(bets[1].stake - bets[0].profit), \
            "Partially matched bet should remain with rest of initial stake/"
    matched_bets = wallet_4hf.get_matched_bets([b.uuid for b in bets])
    assert matched_bets[0]["bet1_data"]["stake"] == str(bets[0].stake), \
        "Better with lesser potential reward should bet whole stake"
    assert matched_bets[0]["bet2_data"]["stake"] == str(bets[0].profit), \
        "Better with greater potential reward should bet stake == profit of opponent"


@pytest.mark.skip_long_term  # test time ~164 sec
def test_betting_flow_close_to_real_game(wallet_4hf: Wallet, real_game_data):
    balances_before = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    empower_betting_moderator(wallet_4hf, DEFAULT_WITNESS)
    change_resolve_delay(wallet_4hf, 3)
    game_uuid, _ = create_game(wallet_4hf, start=3, delay=3600, market_types=real_game_data['markets'])
    for bet in real_game_data['bets']:
        post_bet(
            wallet_4hf, bet.account, game_uuid, wincase_type=bet.wincase, odds=bet.odds, stake=str(bet.stake)
        )
    pending_bets = wallet_4hf.lookup_pending_bets(-1, 100)
    assert len(pending_bets) == 6, "Expected 6 pending bets remain."
    matched_bets = wallet_4hf.lookup_matched_bets(-1, 100)
    assert len(matched_bets) == 28, "Expected 28 matched bets."
    balances_after_betting = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    assert all(
        balances_after_betting[n] == balances_before[n] - real_game_data['expected_outgo'][n]
        for n in real_game_data['betters']
    )
    response = wallet_4hf.post_game_results(game_uuid, DEFAULT_WITNESS, real_game_data['wincases'])
    wallet_4hf.get_block(response['block_num'] + 1, wait_for_block=True)
    balances_after_finish = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    assert all(
        balances_after_finish[n] == balances_after_betting[n] + real_game_data['expected_income'][n]
        for n in real_game_data['betters']
    )
