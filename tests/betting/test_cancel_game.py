import pytest

from automation.wallet import Wallet
from scorum.graphenebase.betting import wincase, market
from tests.betting.conftest import empower_betting_moderator, create_game, create_game_with_bets
from tests.common import (
    validate_response, check_virt_ops, DEFAULT_WITNESS, validate_error_response, gen_uid,
    RE_OBJECT_NOT_EXIST, RE_NOT_MODERATOR, RE_MISSING_AUTHORITY
)


@pytest.mark.parametrize('moderator', [DEFAULT_WITNESS])
def test_cancel_game(wallet: Wallet, moderator):
    empower_betting_moderator(wallet, moderator)
    uuid, _ = create_game(wallet, moderator, delay=3600)
    response = wallet.cancel_game(uuid, moderator)
    validate_response(response, wallet.cancel_game.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["cancel_game"])
    assert wallet.get_games_by_uuids([uuid]) == [], "All games should be closed"


def test_cancel_game_invalid_uuid(wallet: Wallet):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    response = wallet.cancel_game(gen_uid(), DEFAULT_WITNESS)
    validate_error_response(response, wallet.cancel_game.__name__, RE_OBJECT_NOT_EXIST)


@pytest.mark.parametrize('moderator', ['alice'])
def test_cancel_game_same_uuid(wallet: Wallet, moderator):
    empower_betting_moderator(wallet, moderator)
    uuid, _ = create_game(wallet, moderator, delay=3600)
    wallet.cancel_game(uuid, moderator)
    response = wallet.cancel_game(uuid, moderator)
    validate_error_response(response, wallet.cancel_game.__name__, RE_OBJECT_NOT_EXIST)


def test_cancel_game_not_moderator(wallet: Wallet):
    empower_betting_moderator(wallet, "alice")
    uuid, _ = create_game(wallet, "alice")
    response = wallet.cancel_game(uuid, "bob")
    validate_error_response(response, wallet.cancel_game.__name__, RE_NOT_MODERATOR)


def test_cancel_game_invalid_signing(wallet: Wallet):
    empower_betting_moderator(wallet, "alice")
    uuid, _ = create_game(wallet, "alice")
    g = {"uuid": uuid, "moderator": "alice"}
    response = wallet.broadcast_multiple_ops("cancel_game", [g], ["bob"])
    validate_error_response(response, "cancel_game", RE_MISSING_AUTHORITY)


@pytest.mark.parametrize('start', [1, 30])
def test_cancel_game_with_bets(wallet: Wallet, start, bets):
    names = [b.account for b in bets]
    accounts_before = {a["name"]: a for a in wallet.get_accounts(names)}
    game_uuid, bet_uuids = create_game_with_bets(wallet, start, bets)
    wallet.cancel_game(game_uuid, DEFAULT_WITNESS)
    accounts_after = {a["name"]: a for a in wallet.get_accounts(names)}
    assert 0 == len(wallet.get_matched_bets(bet_uuids)), "Matched bets should be cancelled."
    assert 0 == len(wallet.get_pending_bets(bet_uuids)), "Pending bets should be cancelled."
    assert all(accounts_after[name]["balance"] == accounts_before[name]["balance"] for name in names), \
        "All accounts should receive back their stakes."


@pytest.mark.parametrize('moderator', [DEFAULT_WITNESS])
def test_cancel_finished_game(wallet: Wallet, moderator):
    empower_betting_moderator(wallet, moderator)
    uuid, _ = create_game(wallet, moderator, start=1, delay=3600, market_types=[market.RoundHome()])
    wallet.post_game_results(uuid, moderator, [wincase.RoundHomeYes()])
    response = wallet.cancel_game(uuid, moderator)
    validate_error_response(response, wallet.cancel_game.__name__, "Cannot cancel the game after it is finished")


def test_cancel_finished_game_with_matched_bets(wallet: Wallet, matched_bets):
    game_uuid, bet_uuids = create_game_with_bets(wallet, 1, matched_bets)
    wallet.post_game_results(game_uuid, DEFAULT_WITNESS, [wincase.RoundHomeYes(), wincase.HandicapOver(500)])
    wallet.cancel_game(game_uuid, DEFAULT_WITNESS)
    response = wallet.get_matched_bets(bet_uuids)
    assert len(response) == 1, "Matched bets shouldn't be cancelled."
    assert set(bet_uuids) == {response[0]["bet1_data"]["uuid"], response[0]["bet2_data"]["uuid"]}, \
        "Matched bets uuids has unexpectedly changed"
