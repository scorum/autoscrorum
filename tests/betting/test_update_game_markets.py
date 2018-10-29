import pytest
import json

from automation.wallet import Wallet
from tests.betting.conftest import empower_betting_moderator, create_game
from scorum.graphenebase.betting import market, Market
from tests.common import validate_response, check_virt_ops, DEFAULT_WITNESS


@pytest.mark.parametrize('default_market,new_market', [
    (market.TotalGoalsAway(10), market.TotalGoalsHome(100))
])
def test_update_game_markets(wallet: Wallet, default_market, new_market):
    empower_betting_moderator(wallet, DEFAULT_WITNESS)
    uuid, _ = create_game(wallet, DEFAULT_WITNESS, start=30, delay=3600, market_types=[default_market])
    response = wallet.update_game_markets(uuid, DEFAULT_WITNESS, [new_market])
    validate_response(response, wallet.update_game_markets.__name__)
    check_virt_ops(wallet, response['block_num'], response['block_num'], ["update_game_markets"])
    games = wallet.get_games_by_uuids([uuid])
    assert games[0]['markets'][0] == json.loads(str(Market(new_market)))
    assert games[0]['markets'][0] != json.loads(str(Market(default_market)))
