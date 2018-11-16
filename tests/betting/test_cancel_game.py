import pytest
from scorum.graphenebase.betting import wincase, market

from tests.common import (
    validate_response, check_virt_ops, DEFAULT_WITNESS, validate_error_response, gen_uid,
    RE_OBJECT_NOT_EXIST, RE_NOT_MODERATOR, RE_MISSING_AUTHORITY
)


def test_cancel_game(wallet_4hf, betting):
    uuid, _ = betting.create_game(delay=3600)
    response = wallet_4hf.cancel_game(uuid, betting.moderator)
    validate_response(response, wallet_4hf.cancel_game.__name__)
    check_virt_ops(wallet_4hf, response['block_num'], expected_ops=["cancel_game"])
    assert wallet_4hf.get_games_by_uuids([uuid]) == [], "All games should be closed"


def test_cancel_game_invalid_uuid(wallet_4hf, betting):
    response = wallet_4hf.cancel_game(gen_uid(), DEFAULT_WITNESS)
    validate_error_response(response, wallet_4hf.cancel_game.__name__, RE_OBJECT_NOT_EXIST)


def test_cancel_game_same_uuid(wallet_4hf, betting):
    uuid, _ = betting.create_game(delay=3600)
    wallet_4hf.cancel_game(uuid, betting.moderator)
    response = wallet_4hf.cancel_game(uuid, betting.moderator)
    validate_error_response(response, wallet_4hf.cancel_game.__name__, RE_OBJECT_NOT_EXIST)


def test_cancel_game_not_moderator(wallet_4hf, betting):
    uuid, _ = betting.create_game()
    response = wallet_4hf.cancel_game(uuid, "alice")
    validate_error_response(response, wallet_4hf.cancel_game.__name__, RE_NOT_MODERATOR)


def test_cancel_game_invalid_signing(wallet_4hf, betting):
    uuid, _ = betting.create_game()
    g = {"uuid": uuid, "moderator": betting.moderator}
    response = wallet_4hf.broadcast_multiple_ops("cancel_game", [g], ["bob"])
    validate_error_response(response, "cancel_game", RE_MISSING_AUTHORITY)


@pytest.mark.parametrize('start', [1, 30])
def test_cancel_game_with_bets(wallet_4hf, betting, start, bets):
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    game_uuid = betting.create_game_with_bets(bets, game_start=start)
    wallet_4hf.cancel_game(game_uuid, DEFAULT_WITNESS)
    accounts_after = {a["name"]: a for a in wallet_4hf.get_accounts(names)}
    assert 0 == len(wallet_4hf.get_matched_bets([b.uuid for b in bets])), "Matched bets should be cancelled."
    assert 0 == len(wallet_4hf.get_pending_bets([b.uuid for b in bets])), "Pending bets should be cancelled."
    assert all(accounts_after[name]["balance"] == accounts_before[name]["balance"] for name in names), \
        "All accounts should receive back their stakes."


def test_cancel_game_with_bets_few_games(wallet_4hf, betting):
    game1, _ = betting.create_game(start=30, delay=3600, market_types=[market.RoundHome()])
    game2, _ = betting.create_game(start=30, delay=3600, market_types=[market.RoundHome()])
    bet1, _ = betting.post_bet("alice", game1, wincase_type=wincase.RoundHomeYes())
    bet2, _ = betting.post_bet("bob", game2, wincase_type=wincase.RoundHomeNo())
    wallet_4hf.cancel_game(game1, DEFAULT_WITNESS)
    games = wallet_4hf.get_games_by_uuids([game1, game2])
    assert len(games) == 1 and games[0]['uuid'] == game2
    bets = wallet_4hf.get_pending_bets([bet1, bet2])
    assert len(bets) == 1 and bets[0]['data']['uuid'] == bet2


def test_cancel_finished_game(wallet_4hf, betting):
    uuid, _ = betting.create_game(start=1, delay=3600, market_types=[market.RoundHome()])
    wallet_4hf.post_game_results(uuid, betting.moderator, [wincase.RoundHomeYes()])
    response = wallet_4hf.cancel_game(uuid, betting.moderator)
    validate_error_response(response, wallet_4hf.cancel_game.__name__, "Cannot cancel the game after it is finished")


def test_cancel_finished_game_with_matched_bets(wallet_4hf, betting, matched_bets):
    game_uuid = betting.create_game_with_bets(matched_bets, game_start=1)
    wallet_4hf.post_game_results(game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    wallet_4hf.cancel_game(game_uuid, DEFAULT_WITNESS)
    response = wallet_4hf.get_matched_bets([b.uuid for b in matched_bets])
    assert len(response) == 1, "Matched bets shouldn't be cancelled."
    assert set([b.uuid for b in matched_bets]) == {response[0]["bet1_data"]["uuid"], response[0]["bet2_data"]["uuid"]},\
        "Matched bets uuids has unexpectedly changed"
