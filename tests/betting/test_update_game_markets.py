import json

import pytest
from scorum.graphenebase.betting import market, Market, wincase

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game, create_game_with_bets, post_bet
from tests.common import (
    validate_response, check_virt_ops, DEFAULT_WITNESS, RE_OBJECT_NOT_EXIST, validate_error_response, gen_uid,
    RE_NOT_MODERATOR, RE_MISSING_AUTHORITY
)


@pytest.mark.parametrize('default_markets,new_markets', [
    ([market.RoundHome()], [market.Handicap(-1000)]),
    ([market.RoundHome(), market.TotalGoalsAway(500)], [market.TotalGoalsHome(1500)]),
    ([market.Handicap(500)], [market.Handicap(-500)]),
    ([], [market.Handicap(-500)]),
    ([market.Handicap(500)], [])
])
def test_update_game_markets(wallet_4hf: Wallet, default_markets, new_markets):
    empower_betting_moderator(wallet_4hf, DEFAULT_WITNESS)
    uuid, _ = create_game(wallet_4hf, DEFAULT_WITNESS, start=30, delay=3600, market_types=default_markets)
    response = wallet_4hf.update_game_markets(uuid, DEFAULT_WITNESS, new_markets)
    validate_response(response, wallet_4hf.update_game_markets.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["update_game_markets"])
    games = wallet_4hf.get_games_by_uuids([uuid])
    assert games[0]['markets'] == [json.loads(str(Market(m))) for m in new_markets]
    assert games[0]['markets'] != [json.loads(str(Market(m))) for m in default_markets]


def test_update_started_game_markets(wallet_4hf: Wallet):
    # You could add markets, but can't remove them
    empower_betting_moderator(wallet_4hf)
    uuid, _ = create_game(wallet_4hf, start=1, market_types=[market.RoundHome()])
    response = wallet_4hf.update_game_markets(uuid, DEFAULT_WITNESS, [])
    validate_error_response(
        response, wallet_4hf.update_game_markets.__name__, "Cannot cancel markets after game was started"
    )


def test_update_finished_game_markets(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf)
    uuid, _ = create_game(wallet_4hf, start=1, market_types=[market.RoundHome()])
    wallet_4hf.post_game_results(uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes()])
    response = wallet_4hf.update_game_markets(uuid, DEFAULT_WITNESS, [market.ResultHome()])
    validate_error_response(
        response, wallet_4hf.update_game_markets.__name__, "Cannot change the markets when game is finished"
    )


def test_update_game_markets_invalid_uuid(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf, DEFAULT_WITNESS)
    response = wallet_4hf.update_game_markets(gen_uid(), DEFAULT_WITNESS, [])
    validate_error_response(response, wallet_4hf.update_game_markets.__name__, RE_OBJECT_NOT_EXIST)


def test_update_game_markets_not_moderator(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf, "alice")
    uuid, _ = create_game(wallet_4hf, "alice")
    response = wallet_4hf.update_game_markets(uuid, "bob", [market.RoundHome()])
    validate_error_response(response, wallet_4hf.update_game_markets.__name__, RE_NOT_MODERATOR)


def test_update_game_markets_invalid_signing(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf, "alice")
    uuid, _ = create_game(wallet_4hf, "alice")
    g = {"uuid": uuid, "moderator": "alice", "markets": []}
    response = wallet_4hf.broadcast_multiple_ops("update_game_markets", [g], ["bob"])
    validate_error_response(response, "update_game_markets", RE_MISSING_AUTHORITY)


def test_update_game_markets_with_bets(wallet_4hf: Wallet, bets):
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    game_uuid = create_game_with_bets(wallet_4hf, bets)
    wallet_4hf.update_game_markets(game_uuid, DEFAULT_WITNESS, [])
    accounts_after = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    assert 0 == len(wallet_4hf.get_matched_bets([b.uuid for b in bets])), "Matched bets should be cancelled."
    assert 0 == len(wallet_4hf.get_pending_bets([b.uuid for b in bets])), "Pending bets should be cancelled."
    assert all(accounts_after[name]["balance"] == accounts_before[name]["balance"] for name in names), \
        "All accounts should receive back their stakes."


def test_update_game_markets_with_bets_few_games(wallet_4hf: Wallet):
    empower_betting_moderator(wallet_4hf)
    game1, _ = create_game(wallet_4hf, start=30, delay=3600, market_types=[market.RoundHome()])
    game2, _ = create_game(wallet_4hf, start=30, delay=3600, market_types=[market.RoundHome()])
    bet1, _ = post_bet(wallet_4hf, "alice", game1, wincase_type=wincase.RoundHomeYes())
    bet2, _ = post_bet(wallet_4hf, "bob", game2, wincase_type=wincase.RoundHomeNo())
    wallet_4hf.update_game_markets(game1, DEFAULT_WITNESS, [market.Total(1000)])
    games = wallet_4hf.get_games_by_uuids([game1, game2])
    assert games[0]["uuid"] == game1 and games[0]["markets"][0][0] == "total"
    assert games[1]["uuid"] == game2 and games[1]["markets"][0][0] == "round_home"
    bets = wallet_4hf.get_pending_bets([bet1, bet2])
    assert len(bets) == 1 and bets[0]['data']['uuid'] == bet2
