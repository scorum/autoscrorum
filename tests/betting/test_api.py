from automation.wallet import Wallet
from tests.betting.conftest import GAME_FILTERS, empower_betting_moderator, create_game, post_bet
from tests.common import gen_uid, DEFAULT_WITNESS, validate_response, validate_error_response, RE_OBJECT_NOT_EXIST
from scorum.graphenebase.betting import wincase


def test_get_game_winners(wallet: Wallet):
    validate_error_response(wallet.get_game_winners(gen_uid()), wallet.get_game_winners.__name__, RE_OBJECT_NOT_EXIST)
    empower_betting_moderator(wallet)
    game_uuid, _ = create_game(wallet, delay=3600)
    post_bet(wallet, "alice", game_uuid, wincase_type=wincase.RoundHomeYes(), odds=[3, 2])
    post_bet(wallet, "bob", game_uuid, wincase_type=wincase.RoundHomeNo(), odds=[3, 1])
    response = wallet.get_game_winners(game_uuid)
    validate_response(response, wallet.get_matched_bets.__name__)


def test_get_games_by_status(wallet: Wallet):

    def check(status):
        response = wallet.get_games_by_status([GAME_FILTERS.index(status)])
        validate_response(response, wallet.get_games_by_status.__name__)
        assert len(response) == 1, "Should be '%s' one game." % status
        assert response[0]['uuid'] == uuid

    assert wallet.get_games_by_status([0]) == [], "Games shouldn't be created yet."
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    uuid, block_num = create_game(wallet, DEFAULT_WITNESS, start=5)
    check("created")
    wallet.get_block(block_num + 1, wait_for_block=True)
    check("started")
    wallet.post_game_results(uuid, DEFAULT_WITNESS, [wincase.ResultHomeYes()])
    check("finished")


def test_get_betting_properties(wallet: Wallet):
    validate_response(
        wallet.get_betting_properties(), wallet.get_betting_properties.__name__,
        [('moderator', ''), ('resolve_delay_sec', 86400)]
    )


def test_get_games_by_uuids(wallet: Wallet):
    assert wallet.get_games_by_uuids([gen_uid()]) == [], "Games shouldn't be created yet."
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    uuid, _ = create_game(wallet, DEFAULT_WITNESS, delay=3600)
    response = wallet.get_games_by_uuids([uuid])
    validate_response(response, wallet.get_games_by_uuids.__name__)
    assert len(response) == 1, "Should be created %d game(s)." % 1
    assert response[0]['uuid'] == uuid
    # assert response[0]['moderator'] == DEFAULT_WITNESS


def test_lookup_games_by_id(wallet: Wallet):
    assert wallet.lookup_games_by_id(10001, 100) == [], "Games shouldn't be created yet."
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    uuid, _  = create_game(wallet, DEFAULT_WITNESS, delay=3600)
    response = wallet.lookup_games_by_id(-1, 100)
    validate_response(response, wallet.get_games_by_uuids.__name__)
    assert len(response) == 1, "Should be created one game."
    assert response[0]['uuid'] == uuid
    # assert response[0]['moderator'] == DEFAULT_WITNESS


def test_get_matched_bets(wallet: Wallet):
    assert wallet.get_matched_bets([gen_uid()]) == [], "Bets shouldn't be created yet."
    empower_betting_moderator(wallet)
    game_uuid, _ = create_game(wallet, delay=3600)
    alice_bet, _ = post_bet(wallet, "alice", game_uuid, wincase_type=wincase.RoundHomeYes(), odds=[3, 2])
    bob_bet, _ = post_bet(wallet, "bob", game_uuid, wincase_type=wincase.RoundHomeNo(), odds=[3, 1])
    response = wallet.get_matched_bets([alice_bet, bob_bet])
    validate_response(response, wallet.get_matched_bets.__name__)
    assert response[0]["market"][0] == "round_home"
    assert response[0]["bet1_data"]["uuid"] == alice_bet
    assert response[0]["bet2_data"]["uuid"] == bob_bet


def test_lookup_matched_bets(wallet: Wallet):
    assert wallet.lookup_matched_bets(0, 100) == [], "Bets shouldn't be created yet."
    empower_betting_moderator(wallet)
    game_uuid, _ = create_game(wallet, delay=3600)
    alice_bet, _ = post_bet(wallet, "alice", game_uuid, wincase_type=wincase.RoundHomeYes(), odds=[3, 2])
    bob_bet, _ = post_bet(wallet, "bob", game_uuid, wincase_type=wincase.RoundHomeNo(), odds=[3, 1])
    response = wallet.lookup_matched_bets(-1, 100)
    validate_response(response, wallet.get_matched_bets.__name__)
    assert response[0]["market"][0] == "round_home"
    assert response[0]["bet1_data"]["uuid"] == alice_bet
    assert response[0]["bet2_data"]["uuid"] == bob_bet


def test_get_pending_bets(wallet: Wallet):
    assert wallet.get_pending_bets([gen_uid()]) == [], "Bets shouldn't be created yet."
    empower_betting_moderator(wallet)
    game_uuid, _ = create_game(wallet)
    bet_uuid, _ = post_bet(wallet, "alice", game_uuid)
    response = wallet.get_pending_bets([bet_uuid])
    validate_response(response, wallet.get_pending_bets.__name__)
    assert len(response) == 1
    assert response[0]['data']['uuid'] == bet_uuid


def test_lookup_pending_bets(wallet: Wallet):
    assert wallet.lookup_pending_bets(0, 100) == [], "Bets shouldn't be created yet."
    empower_betting_moderator(wallet)
    game_uuid, _ = create_game(wallet)
    bet_uuid, _ = post_bet(wallet, "alice", game_uuid)
    response = wallet.lookup_pending_bets(-1, 100)
    validate_response(response, wallet.lookup_pending_bets.__name__)
    assert len(response) == 1
    assert response[0]['data']['uuid'] == bet_uuid
