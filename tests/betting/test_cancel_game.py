import pytest

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game
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
