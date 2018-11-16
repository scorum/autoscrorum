import pytest
from scorum.graphenebase.amount import Amount
from scorum.graphenebase.betting import wincase, market

from copy import deepcopy

from tests.betting.betting import Bet
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
def test_post_bet(wallet_4hf, betting, better, market_type, wincase_type, odds, stake, live):
    balance_before = wallet_4hf.get_account_scr_balance(better)
    game_uuid, _ = betting.create_game(DEFAULT_WITNESS, market_types=[market_type])
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
def test_post_bet_invalid_params(wallet_4hf, betting, market_type, wincase_type, odds, stake, live, expected_error):
    game_uuid, _ = betting.create_game(start=1, market_types=[market_type])
    response = wallet_4hf.post_bet(gen_uid(), "alice", game_uuid, wincase_type, odds, stake, live)
    validate_error_response(response, wallet_4hf.post_bet.__name__, expected_error)


def test_post_bet_same_uuid(wallet_4hf, betting):
    game_uuid, _ = betting.create_game(wstart=1, market_types=[market.RoundHome()])
    bet_uuid, _ = betting.post_bet("alice", game_uuid, wincase=wincase.RoundHomeYes())
    wallet_4hf.cancel_pending_bets([bet_uuid], "alice")
    response = wallet_4hf.post_bet(
        bet_uuid, "alice", game_uuid, wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR", True)
    validate_error_response(response, wallet_4hf.post_bet.__name__, RE_OBJECT_EXIST)


def test_post_bet_same_uuid_few_games(wallet_4hf, betting):
    game1, _ = betting.create_game(delay=3600, market_types=[market.RoundHome()])
    game2, _ = betting.create_game(delay=3600, market_types=[market.RoundHome()])
    bet_uuid, _ = betting.post_bet("alice", game1, wincase=wincase.RoundHomeYes())
    response = wallet_4hf.post_bet(
        bet_uuid, "alice", game2, wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR", True
    )
    validate_error_response(response, wallet_4hf.post_bet.__name__, RE_OBJECT_EXIST)


def test_post_bet_auto_resolve(wallet_4hf, betting, bets):
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    betting.create_game_with_bets(bets, game_start=1, delay=6)
    block = max(b.block_creation_num for b in bets)
    wallet_4hf.get_block(block + 1, wait_for_block=True)
    accounts_after = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    assert wallet_4hf.get_pending_bets([b.uuid for b in bets]) == []
    assert wallet_4hf.get_matched_bets([b.uuid for b in bets]) == []
    assert all(accounts_after[name]["balance"] == accounts_before[name]["balance"] for name in names), \
        "All accounts should receive back their stakes."


def test_post_bet_finished_game_resolve(wallet_4hf, betting, bets):
    betting.change_resolve_delay(4)  # resolve game next block after it will be finished
    game_uuid = betting.create_game_with_bets(bets, game_start=1)
    matched_bets = wallet_4hf.lookup_matched_bets(-1, 100)
    response = wallet_4hf.post_game_results(
        game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    winners = wallet_4hf.get_game_winners(game_uuid)
    wallet_4hf.get_block(response["block_num"] + 1, wait_for_block=True)
    if matched_bets:
        check_virt_ops(wallet_4hf, response['block_num'] + 1, expected_ops=["bet_resolved"])
        for w in winners:
            history = wallet_4hf.get_account_history(w['winner']['name'], -1, 1)
            assert history[0][1]['op'][0] == "bet_resolved"
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
        Bet("alice", wincase.RoundHomeYes(), ODDS_MIN, STAKE_MIN),
        Bet("bob", wincase.RoundHomeNo(), ODDS_MAX, "1.000000000 SCR")
    ], False),
    # TODO: Uncomment when integer overflow bug will be fixed
    # ([
    #     Bet("boss", wincase.RoundHomeNo(), ODDS_MAX, "9500000.000000000 SCR"),
    #     Bet("alice", wincase.RoundHomeYes(), ODDS_MIN, "1.000000000 SCR"),
    # ], False)
])
def test_bets_matching(wallet_4hf, betting, bets, full_match):
    betting.create_game_with_bets(bets, game_start=1)
    block = max(b.block_creation_num for b in bets)
    check_virt_ops(wallet_4hf, block, expected_ops=["bets_matched", "bet_cancelled", "bet_updated"])
    pending_bets = wallet_4hf.lookup_pending_bets(-1, 100)
    pending_stake_sum = sum([Amount(b['data']['stake']) for b in pending_bets], Amount())
    if full_match:
        assert len(pending_bets) == 0, "There shouldn't be pending bets."
    else:
        assert len(pending_bets) == 1, "There should be left removed from pending bets"
        assert pending_bets[0]["data"]["stake"] == str(bets[1].stake - bets[0].profit), \
            "Partially matched bet should remain with rest of initial stake/"
    matched_bets = wallet_4hf.get_matched_bets([b.uuid for b in bets])
    matched_stake_sum = sum([
        Amount(b['bet1_data']['stake']) + Amount(b['bet2_data']['stake']) for b in matched_bets], Amount()
    )
    assert matched_bets[0]["bet1_data"]["stake"] == str(bets[0].stake), \
        "Better with lesser potential reward should bet whole stake"
    assert matched_bets[0]["bet2_data"]["stake"] == str(bets[0].profit), \
        "Better with greater potential reward should bet stake == profit of opponent"
    betting_stats = wallet_4hf.get_chain_capital()['betting_stats']
    assert Amount(betting_stats['pending_bets_volume']) == pending_stake_sum
    assert Amount(betting_stats['matched_bets_volume']) == matched_stake_sum


# @pytest.mark.skip_long_term  # test time ~46 sec
def test_betting_flow_close_to_real_game(wallet_4hf, betting, real_game_data):
    balances_before = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    betting.change_resolve_delay(4)
    game_uuid = betting.create_game_with_bets(
        real_game_data['bets'], game_start=3, market_types=real_game_data['markets']
    )
    pending_bets = wallet_4hf.lookup_pending_bets(-1, 100)
    assert len(pending_bets) == 6, "Expected 6 pending bets remain."
    pending_stake_sum = sum([Amount(b['data']['stake']) for b in pending_bets], Amount())
    matched_bets = wallet_4hf.lookup_matched_bets(-1, 100)
    assert len(matched_bets) == 30, "Expected 30 matched bets."
    matched_stake_sum = sum([
        Amount(b['bet1_data']['stake']) + Amount(b['bet2_data']['stake']) for b in matched_bets], Amount()
    )
    betting_stats = wallet_4hf.get_chain_capital()['betting_stats']
    assert Amount(betting_stats['pending_bets_volume']) == pending_stake_sum
    assert Amount(betting_stats['matched_bets_volume']) == matched_stake_sum
    balances_after_betting = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    assert all(
        balances_after_betting[n] == balances_before[n] - real_game_data['expected_outgo'][n]
        for n in real_game_data['betters']
    )
    response = wallet_4hf.post_game_results(game_uuid, DEFAULT_WITNESS, real_game_data['wincases'])
    game_returns = wallet_4hf.get_game_returns(game_uuid)
    assert len(real_game_data["expected_paybacks"]) == len(game_returns), "Unexpected amount of game returns."
    game_winners = wallet_4hf.get_game_winners(game_uuid)
    assert len(matched_bets) - len(game_returns) == len(game_winners), \
        "Unexpected amount of game winners."
    wallet_4hf.get_block(response['block_num'] + 1, wait_for_block=True)
    resolved = check_virt_ops(wallet_4hf, response["block_num"] + 1, expected_ops=["bet_resolved"])
    assert real_game_data['expected_resolved_ops'] == len(resolved), "Unexpected amount of 'bet_resolved' operations."
    balances_after_finish = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    assert all(
        balances_after_finish[n] == balances_after_betting[n] + real_game_data['expected_income'][n]
        for n in real_game_data['betters']
    )


# @pytest.mark.skip_long_term  # test time ~61 sec
def test_betting_flow_close_to_real_few_games(wallet_4hf, betting, real_game_data):
    game1 = real_game_data
    game2 = deepcopy(real_game_data)
    balances_before = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    betting.change_resolve_delay(4)
    game1_uuid = betting.create_game_with_bets(
        game1['bets'], game_start=3, market_types=game1['markets']
    )
    game2_uuid = betting.create_game_with_bets(
        game2['bets'], game_start=3, market_types=game2['markets']
    )

    pending_bets = wallet_4hf.lookup_pending_bets(-1, 100)
    assert len(pending_bets) == 12, "Expected 12 pending bets remain."
    pending_stake_sum = sum([Amount(b['data']['stake']) for b in pending_bets], Amount())
    matched_bets = wallet_4hf.lookup_matched_bets(-1, 100)
    assert len(matched_bets) == 60, "Expected 60 matched bets."
    matched_stake_sum = sum([
        Amount(b['bet1_data']['stake']) + Amount(b['bet2_data']['stake']) for b in matched_bets], Amount()
    )
    betting_stats = wallet_4hf.get_chain_capital()['betting_stats']
    assert Amount(betting_stats['pending_bets_volume']) == pending_stake_sum
    assert Amount(betting_stats['matched_bets_volume']) == matched_stake_sum

    balances_after_betting = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    assert all(
        balances_after_betting[n] == balances_before[n] - game1['expected_outgo'][n] - game2['expected_outgo'][n]
        for n in real_game_data['betters']
    )

    response = wallet_4hf.post_game_results(game1_uuid, DEFAULT_WITNESS, game1['wincases'])
    game1_returns = wallet_4hf.get_game_returns(game1_uuid)
    assert len(game1["expected_paybacks"]) == len(game1_returns), "Unexpected amount of game returns."
    game1_winners = wallet_4hf.get_game_winners(game1_uuid)
    wallet_4hf.get_block(response['block_num'] + 1, wait_for_block=True)
    resolved = check_virt_ops(wallet_4hf, response["block_num"] + 1, expected_ops=["bet_resolved"])
    assert game1['expected_resolved_ops'] == len(resolved), "Unexpected amount of 'bet_resolved' operations."

    response = wallet_4hf.post_game_results(game2_uuid, DEFAULT_WITNESS, game2['wincases'])
    game2_returns = wallet_4hf.get_game_returns(game2_uuid)
    assert len(game2["expected_paybacks"]) == len(game2_returns), "Unexpected amount of game returns."
    game2_winners = wallet_4hf.get_game_winners(game2_uuid)

    assert len(matched_bets) - len(game1_returns) - len(game2_returns) == len(game1_winners) + len(game2_winners), \
        "Unexpected amount of game winners."

    wallet_4hf.get_block(response['block_num'] + 1, wait_for_block=True)
    resolved = check_virt_ops(wallet_4hf, response["block_num"] + 1, expected_ops=["bet_resolved"])
    assert game2["expected_resolved_ops"] == len(resolved), "Unexpected amount of 'bet_resolved' operations."
    balances_after_finish = wallet_4hf.get_accounts_balances(real_game_data['betters'])
    assert all(
        balances_after_finish[n] == balances_after_betting[n] +
        game1['expected_income'][n] + game2['expected_income'][n]
        for n in real_game_data['betters']
    )
