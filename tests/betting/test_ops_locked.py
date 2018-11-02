import pytest
from scorum.utils.time import fmt_time_from_now
from scorum.graphenebase.betting import market, wincase, game

from automation.wallet import Wallet
from tests.common import DEFAULT_WITNESS, RE_OP_IS_LOCKED, validate_error_response, gen_uid, RE_OBJECT_NOT_EXIST

"""
Betting functions and operations should be locked until 3rd hardfork.
"""

create_game_data = {
    "uuid": gen_uid(),
    "moderator": DEFAULT_WITNESS,
    "json_metadata": "{}",
    "start_time": fmt_time_from_now(30),
    "auto_resolve_delay_sec": 3600,
    "game": game.Soccer(),
    "markets": [market.RoundHome()],
}

cancel_game_data = {
    "uuid": gen_uid(),
    "moderator": DEFAULT_WITNESS,
}

update_game_markets_data = {
    "uuid": gen_uid(),
    "moderator": DEFAULT_WITNESS,
    "markets": [market.RoundHome()],
}

update_game_start_time_data = {
    "uuid": gen_uid(),
    "moderator": DEFAULT_WITNESS,
    "start_time": fmt_time_from_now(30),
}

post_bet_data = {
    "uuid": gen_uid(),
    "better": DEFAULT_WITNESS,
    "game_uuid": gen_uid(),
    "wincase": wincase.RoundHomeYes(),
    "odds": [1, 2],
    "stake": "1.000000000 SCR",
    "live": True
}

post_game_results_data = {
    "uuid": gen_uid(),
    "moderator": DEFAULT_WITNESS,
    "wincases": [wincase.RoundHomeYes()],
}

cancel_pending_bets_data = {
    "uuids": [gen_uid()],
    "better": DEFAULT_WITNESS,
}

development_committee_empower_betting_moderator_data = {
    "initiator": DEFAULT_WITNESS,
    "moderator": DEFAULT_WITNESS,
    "lifetime_sec": 86400
}

development_committee_change_betting_resolve_delay_data = {
    "initiator": DEFAULT_WITNESS,
    "delay_sec": 60,
    "lifetime_sec": 86400
}


@pytest.mark.parametrize('op_name, data', [
    ("create_game", create_game_data),
    ("cancel_game", cancel_game_data),
    ("update_game_markets", update_game_markets_data),
    ("update_game_start_time", update_game_start_time_data),
    ("post_game_results", post_game_results_data),
    ("post_bet", post_bet_data),
    ("cancel_pending_bets", cancel_pending_bets_data),
    ("development_committee_empower_betting_moderator", development_committee_empower_betting_moderator_data),
    ("development_committee_change_betting_resolve_delay", development_committee_change_betting_resolve_delay_data)
])
def test_betting_operations_locked(wallet: Wallet, op_name, data):
    response = wallet.broadcast_multiple_ops(op_name, [data], [DEFAULT_WITNESS])
    validate_error_response(response, wallet.create_budget.__name__, RE_OP_IS_LOCKED)


@pytest.mark.parametrize('func_name, params, expected_result', [
    ('get_game_winners', ["f8456fdb-63fc-423d-9c7d-f6a82c57f8c3"], RE_OBJECT_NOT_EXIST),
    ('get_games_by_status', [[0]], []),
    ('get_games_by_uuids', [["f8456fdb-63fc-423d-9c7d-f6a82c57f8c3"]], []),
    ('lookup_games_by_id', [-1, 100], []),
    ('lookup_matched_bets', [-1, 100], []),
    ('lookup_pending_bets', [-1, 100], []),
    ('get_matched_bets', [["f8456fdb-63fc-423d-9c7d-f6a82c57f8c3"]], []),
    ('get_pending_bets', [["f8456fdb-63fc-423d-9c7d-f6a82c57f8c3"]], []),
    ('get_betting_properties', [], {'id': 0, 'moderator': '', 'resolve_delay_sec': 86400})
])
def test_api_functions_locked(wallet: Wallet, func_name, params, expected_result):
    response = wallet.rpc.send(wallet.json_rpc_body('call', 'betting_api', func_name, params))
    assert response.get("result") == expected_result or validate_error_response(response, func_name, expected_result)
