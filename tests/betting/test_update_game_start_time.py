import pytest
from scorum.graphenebase.betting import wincase, market
from scorum.utils.time import to_date, date_to_str, fmt_time_from_now

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game, create_game_with_bets, post_bet, Bet
from tests.common import (
    validate_response, check_virt_ops, DEFAULT_WITNESS, validate_error_response, gen_uid,
    RE_OBJECT_NOT_EXIST, RE_NOT_MODERATOR, RE_MISSING_AUTHORITY, RE_START_TIME
)


@pytest.mark.parametrize('start,time_shift', [
    (30, 30),  # shift forward
    (30, -10)  # shift backward
])
def test_update_game_start_time(wallet_4hf: Wallet, start, time_shift):
    empower_betting_moderator(wallet_4hf, DEFAULT_WITNESS)
    uuid, _ = create_game(wallet_4hf, DEFAULT_WITNESS, start=start, delay=3600)
    game_before = wallet_4hf.get_games_by_uuids([uuid])[0]
    start_time = date_to_str(to_date(game_before['start_time'], tmdelta={'seconds': time_shift}))
    response = wallet_4hf.update_game_start_time(uuid, DEFAULT_WITNESS, start_time)
    validate_response(response, wallet_4hf.update_game_start_time.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["update_game_start_time"])
    game_after = wallet_4hf.get_games_by_uuids([uuid])[0]
    assert game_before['start_time'] != game_after['start_time']
    assert game_after['start_time'] == start_time


@pytest.mark.parametrize('start,shift,expected_error', [
    (10, -30, RE_START_TIME),  # created game
    (1, -30, RE_START_TIME),  # started game
    (10, 44000, "Cannot change start time more than .* seconds")
])
def test_update_game_start_time_invalid_time(wallet_4hf: Wallet, start, shift, expected_error):
    empower_betting_moderator(wallet_4hf)
    uuid, _ = create_game(wallet_4hf, start=start)
    response = wallet_4hf.update_game_start_time(uuid, DEFAULT_WITNESS, fmt_time_from_now(shift))
    validate_error_response(response, wallet_4hf.update_game_start_time.__name__, expected_error)


def test_update_finished_game_start_time(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf)
    uuid, _ = create_game(wallet_4hf, start=1, market_types=[market.RoundHome()])
    wallet_4hf.post_game_results(uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes()])
    response = wallet_4hf.update_game_start_time(uuid, DEFAULT_WITNESS, fmt_time_from_now(30))
    validate_error_response(
        response, wallet_4hf.update_game_start_time.__name__, "Cannot change the start time when game is finished"
    )


def test_update_game_start_time_invalid_uuid(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf, DEFAULT_WITNESS)
    response = wallet_4hf.update_game_start_time(gen_uid(), DEFAULT_WITNESS, fmt_time_from_now(30))
    validate_error_response(response, wallet_4hf.update_game_start_time.__name__, RE_OBJECT_NOT_EXIST)


def test_update_game_start_time_not_moderator(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf, "alice")
    uuid, _ = create_game(wallet_4hf, "alice")
    response = wallet_4hf.update_game_start_time(uuid, "bob", fmt_time_from_now(30))
    validate_error_response(response, wallet_4hf.update_game_start_time.__name__, RE_NOT_MODERATOR)


def test_update_game_start_time_invalid_signing(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf, "alice")
    uuid, _ = create_game(wallet_4hf, "alice")
    g = {"uuid": uuid, "moderator": "alice", "start_time": fmt_time_from_now(30)}
    response = wallet_4hf.broadcast_multiple_ops("update_game_start_time", [g], ["bob"])
    validate_error_response(response, "update_game_start_time", RE_MISSING_AUTHORITY)


def test_update_start_time_of_game_with_matched_bets_before_start(wallet_4hf: Wallet, matched_bets):
    game_uuid = create_game_with_bets(wallet_4hf, matched_bets)
    wallet_4hf.update_game_start_time(game_uuid, DEFAULT_WITNESS, fmt_time_from_now(30))
    response = wallet_4hf.get_matched_bets([b.uuid for b in matched_bets])
    assert len(response) == 1, "Bets matched before start time shouldn't be cancelled."
    assert set([b.uuid for b in matched_bets]) == {response[0]["bet1_data"]["uuid"], response[0]["bet2_data"]["uuid"]},\
        "Matched bets uuids has unexpectedly changed"


def test_update_start_time_of_game_with_pending_bets_before_start(wallet_4hf: Wallet, pending_bets):
    game_uuid = create_game_with_bets(wallet_4hf, pending_bets)
    wallet_4hf.update_game_start_time(game_uuid, DEFAULT_WITNESS, fmt_time_from_now(30))
    response = wallet_4hf.get_pending_bets([b.uuid for b in pending_bets])
    assert len(response) == 2, "Bets added before start time shouldn't be cancelled."
    assert set([b.uuid for b in pending_bets]) == set(r["data"]["uuid"] for r in response),\
        "Pending bets uuids has unexpectedly changed"


def test_update_start_time_of_game_with_bets_added_after_start(wallet_4hf: Wallet, bets):
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    game_uuid = create_game_with_bets(wallet_4hf, bets, game_start=1)
    wallet_4hf.update_game_start_time(game_uuid, DEFAULT_WITNESS, fmt_time_from_now(30))
    accounts_after = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    response = wallet_4hf.get_matched_bets([b.uuid for b in bets])
    assert len(response) == 0, "Bets added after start time should be cancelled."
    assert all(accounts_after[name]["balance"] == accounts_before[name]["balance"] for name in names), \
        "All accounts should receive back their stakes."


def test_update_game_start_time_with_bets_few_games(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf)
    game1, _ = create_game(wallet_4hf, delay=3600, market_types=[market.RoundHome()])
    game2, _ = create_game(wallet_4hf, delay=3600, market_types=[market.RoundHome()])
    bet1, _ = post_bet(wallet_4hf, "alice", game1, wincase_type=wincase.RoundHomeYes())
    bet2, _ = post_bet(wallet_4hf, "bob", game2, wincase_type=wincase.RoundHomeNo())
    wallet_4hf.update_game_start_time(game1, DEFAULT_WITNESS, fmt_time_from_now(30))
    bets = wallet_4hf.get_pending_bets([bet1, bet2])
    assert len(bets) == 1 and bets[0]['data']['uuid'] == bet2, \
        "Should remain only pending bet in not changed game."


@pytest.mark.parametrize('bets, expected_ops', [
    (
        [Bet("alice", wincase.HandicapOver(500), [2, 1]), Bet("bob", wincase.HandicapUnder(500), [2, 1])],
        ["bet_restored", "bet_cancelled"]  # fully matched bet should be restored
    ),
    (
        [Bet("alice", wincase.HandicapOver(500), [3, 1]), Bet("bob", wincase.HandicapUnder(500), [3, 2])],
        ["bet_updated", "bet_cancelled"]  # partially matched bet shouldn't be re-created
    )
])
def test_update_start_time_restore_bets(wallet_4hf: Wallet, bets, expected_ops):
    game_uuid = create_game_with_bets(wallet_4hf, game_start=5, delay=3600, bets=bets, single_block=False)
    response = wallet_4hf.update_game_start_time(game_uuid, DEFAULT_WITNESS, fmt_time_from_now(30))
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=expected_ops)
    assert wallet_4hf.lookup_matched_bets(-1, 100) == [], "Matched bets should be cancelled."
    pending_bets = wallet_4hf.lookup_pending_bets(-1, 100)
    assert len(pending_bets) == 1, "Should exist only bet created before game has started."
    assert pending_bets[0]["data"]["uuid"] == bets[0].uuid
