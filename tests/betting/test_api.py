from scorum.graphenebase.betting import wincase, market

from tests.betting.conftest import GAME_FILTERS
from tests.common import gen_uid, DEFAULT_WITNESS, validate_response, validate_error_response, RE_OBJECT_NOT_EXIST


def test_get_game_winners(wallet_4hf, betting, matched_bets):
    validate_error_response(
        wallet_4hf.get_game_winners(gen_uid()), wallet_4hf.get_game_winners.__name__, RE_OBJECT_NOT_EXIST
    )
    game_uuid = betting.create_game_with_bets(matched_bets, game_start=1)
    wallet_4hf.post_game_results(game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    response = wallet_4hf.get_game_winners(game_uuid)
    validate_response(response, wallet_4hf.get_matched_bets.__name__)
    assert response, "At least one winner should present in response"


def test_get_games_by_status(wallet_4hf, betting):

    def check(status):
        response = wallet_4hf.get_games_by_status([GAME_FILTERS.index(status)])
        validate_response(response, wallet_4hf.get_games_by_status.__name__)
        assert len(response) == 1, "Should be '%s' one game." % status
        assert response[0]['uuid'] == uuid

    assert wallet_4hf.get_games_by_status([0]) == [], "Games shouldn't be created yet."
    uuid, block_num = betting.create_game(start=5, market_types=[market.ResultHome()])
    check("created")
    wallet_4hf.get_block(block_num + 1, wait_for_block=True)
    check("started")
    wallet_4hf.post_game_results(uuid, DEFAULT_WITNESS, [wincase.ResultHomeYes()])
    check("finished")


def test_get_betting_properties(wallet_4hf):
    default_delay = wallet_4hf.get_config()["SCORUM_BETTING_RESOLVE_DELAY_SEC"]
    validate_response(
        wallet_4hf.get_betting_properties(), wallet_4hf.get_betting_properties.__name__,
        [('moderator', ''), ('resolve_delay_sec', default_delay)]
    )


def test_get_games_by_uuids(wallet_4hf, betting):
    assert wallet_4hf.get_games_by_uuids([gen_uid()]) == [], "Games shouldn't be created yet."
    uuid, _ = betting.create_game(DEFAULT_WITNESS, delay=3600)
    response = wallet_4hf.get_games_by_uuids([uuid])
    validate_response(response, wallet_4hf.get_games_by_uuids.__name__)
    assert len(response) == 1, "Should be created %d game(s)." % 1
    assert response[0]['uuid'] == uuid


def test_lookup_games_by_id(wallet_4hf, betting):
    assert wallet_4hf.lookup_games_by_id(10001, 100) == [], "Games shouldn't be created yet."
    uuid, _ = betting.create_game(DEFAULT_WITNESS, delay=3600)
    response = wallet_4hf.lookup_games_by_id(-1, 100)
    validate_response(response, wallet_4hf.get_games_by_uuids.__name__)
    assert len(response) == 1, "Should be created one game."
    assert response[0]['uuid'] == uuid


def test_get_matched_bets(wallet_4hf, betting):
    assert wallet_4hf.get_matched_bets([gen_uid()]) == [], "Bets shouldn't be created yet."
    betting.empower_betting_moderator()
    game_uuid, _ = betting.create_game(delay=3600, market_types=[market.RoundHome()])
    alice_bet, _ = betting.post_bet("alice", game_uuid, wincase_type=wincase.RoundHomeYes(), odds=[3, 2])
    bob_bet, _ = betting.post_bet("bob", game_uuid, wincase_type=wincase.RoundHomeNo(), odds=[3, 1])
    response = wallet_4hf.get_matched_bets([alice_bet, bob_bet])
    validate_response(response, wallet_4hf.get_matched_bets.__name__)
    assert response[0]["market"][0] == "round_home"
    assert response[0]["bet1_data"]["uuid"] == alice_bet
    assert response[0]["bet2_data"]["uuid"] == bob_bet


def test_get_game_matched_bets(wallet_4hf, betting):
    assert wallet_4hf.get_game_matched_bets(gen_uid()) == [], "Game and bets shouldn't be created yet."
    game_uuid, _ = betting.create_game(delay=3600, market_types=[market.RoundHome()])
    alice_bet, _ = betting.post_bet("alice", game_uuid, wincase_type=wincase.RoundHomeYes(), odds=[3, 2])
    bob_bet, _ = betting.post_bet("bob", game_uuid, wincase_type=wincase.RoundHomeNo(), odds=[3, 1])
    response = wallet_4hf.get_game_matched_bets(game_uuid)
    validate_response(response, wallet_4hf.get_game_matched_bets.__name__)
    assert response[0]["market"][0] == "round_home"
    assert response[0]["bet1_data"]["uuid"] == alice_bet
    assert response[0]["bet2_data"]["uuid"] == bob_bet


def test_lookup_matched_bets(wallet_4hf, betting):
    assert wallet_4hf.lookup_matched_bets(0, 100) == [], "Bets shouldn't be created yet."
    game_uuid, _ = betting.create_game(delay=3600, market_types=[market.RoundHome()])
    alice_bet, _ = betting.post_bet("alice", game_uuid, wincase_type=wincase.RoundHomeYes(), odds=[3, 2])
    bob_bet, _ = betting.post_bet("bob", game_uuid, wincase_type=wincase.RoundHomeNo(), odds=[3, 1])
    response = wallet_4hf.lookup_matched_bets(-1, 100)
    validate_response(response, wallet_4hf.get_matched_bets.__name__)
    assert response[0]["market"][0] == "round_home"
    assert response[0]["bet1_data"]["uuid"] == alice_bet
    assert response[0]["bet2_data"]["uuid"] == bob_bet


def test_get_pending_bets(wallet_4hf, betting):
    assert wallet_4hf.get_pending_bets([gen_uid()]) == [], "Bets shouldn't be created yet."
    game_uuid, _ = betting.create_game(market_types=[market.RoundHome()])
    bet_uuid, _ = betting.post_bet("alice", game_uuid, wincase=wincase.RoundHomeYes())
    response = wallet_4hf.get_pending_bets([bet_uuid])
    validate_response(response, wallet_4hf.get_pending_bets.__name__)
    assert len(response) == 1
    assert response[0]['data']['uuid'] == bet_uuid


def test_get_game_pending_bets(wallet_4hf, betting):
    assert wallet_4hf.get_game_pending_bets(gen_uid()) == [], "Game and bets shouldn't be created yet."
    game_uuid, _ = betting.create_game(market_types=[market.RoundHome()])
    bet_uuid, _ = betting.post_bet("alice", game_uuid, wincase=wincase.RoundHomeYes())
    response = wallet_4hf.get_game_pending_bets(game_uuid)
    validate_response(response, wallet_4hf.get_game_pending_bets.__name__)
    assert len(response) == 1
    assert response[0]['data']['uuid'] == bet_uuid


def test_lookup_pending_bets(wallet_4hf, betting):
    assert wallet_4hf.lookup_pending_bets(0, 100) == [], "Bets shouldn't be created yet."
    game_uuid, _ = betting.create_game(market_types=[market.RoundHome()])
    bet_uuid, _ = betting.post_bet("alice", game_uuid, wincase=wincase.RoundHomeYes())
    response = wallet_4hf.lookup_pending_bets(-1, 100)
    validate_response(response, wallet_4hf.lookup_pending_bets.__name__)
    assert len(response) == 1
    assert response[0]['data']['uuid'] == bet_uuid


def test_get_game_returns(wallet_4hf, betting, matched_bets):
    validate_error_response(
        wallet_4hf.get_game_returns(gen_uid()), wallet_4hf.get_game_returns.__name__, RE_OBJECT_NOT_EXIST
    )
    matched_bets[0].wincase = wincase.HandicapOver()
    matched_bets[1].wincase = wincase.HandicapUnder()
    game_uuid = betting.create_game_with_bets(matched_bets, market_types=[market.Handicap()], game_start=1)
    wallet_4hf.post_game_results(game_uuid, DEFAULT_WITNESS, [])
    response = wallet_4hf.get_game_returns(game_uuid)
    validate_response(response, wallet_4hf.get_game_returns.__name__)
    assert response, "Expected non-empty returns list."
