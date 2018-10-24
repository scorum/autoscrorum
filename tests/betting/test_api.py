import pytest

from automation.wallet import Wallet
from tests.betting.conftest import GAME_FILTERS


@pytest.mark.parametrize('uuid', ['e629f9aa-6b2c-46aa-8fa8-36770e7a7a5f'])
def test_get_game_winners(wallet: Wallet, uuid):
    assert wallet.get_game_winners(uuid) is None, "Winners shouldn't be set yet."
    # create game, end game
    # response = wallet.get_game_winners(uuid)
    # validate_response(response, wallet.get_game_winners.__name__)


@pytest.mark.parametrize('filter', [GAME_FILTERS.index("created")])
def test_get_games(wallet: Wallet, filter):
    assert wallet.get_games(filter) is None, "Games shouldn't be created yet."
    # create game
    # response = wallet.get_gameS(filter)
    # validate_response(response, wallet.get_games.__name__)


