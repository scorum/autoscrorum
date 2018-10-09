import json

import pytest
from src.wallet import Wallet
from graphenebase.amount import Amount
from tests.advertising.conftest import update_budget_time, update_budget_balance
from tests.common import (
    validate_response, validate_error_response, check_virt_ops, RE_PARSE_ERROR, RE_BUDGET_NOT_EXIST, MAX_INT_64
)


@pytest.mark.parametrize('json_metadata', [json.dumps({"meta": "some_meta"}), "{\"meta\": \"some_meta\"}", "{}"])
def test_update_budget(wallet_3hf: Wallet, budget, json_metadata):
    update_budget_time(wallet_3hf, budget)
    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)
    response = wallet_3hf.update_budget(budget['type'], budget['id'], budget['owner'], json_metadata)
    validate_response(response, wallet_3hf.update_budget.__name__, [('block_num', int)])
    check_virt_ops(wallet_3hf, response["block_num"], response["block_num"], {'update_budget'})
    budget_obj = wallet_3hf.get_budget(budget['id'], budget['type'])
    assert budget_obj['json_metadata'] == json_metadata
    assert Amount(budget_obj['balance']) == Amount(budget['balance']) - Amount(budget['per_block'])
    assert Amount(budget_obj['budget_pending_outgo']) == Amount(budget['budget_pending_outgo']) + \
        Amount(budget['per_block'])
    changed = {"json_metadata", 'balance', 'budget_pending_outgo'}
    assert all(budget[k] == budget_obj[k] for k in set(budget.keys()).difference(changed)), \
        'Not only budget metadata changed after update\n' \
        'before: {}\n' \
        'after: {}'.format(budget, budget_obj)


@pytest.mark.parametrize('json_metadata', [json.dumps({"meta": "some_meta"}), "{\"meta\": \"some_meta\"}", "{}"])
def test_update_budget_current_winners(wallet_3hf: Wallet, opened_budgets, json_metadata):
    budget = opened_budgets[0]
    winners_before = wallet_3hf.get_current_winners(budget['type'])
    response = wallet_3hf.update_budget(budget['type'], budget['id'], budget['owner'], json_metadata)
    validate_response(response, wallet_3hf.update_budget.__name__, [('block_num', int)])
    winners_after = wallet_3hf.get_current_winners(budget['type'])
    assert all(winners_before[i]['id'] == winners_after[i]['id'] for i in range(len(winners_before)))


@pytest.mark.parametrize('json_metadata', ["мама мыла раму", "{\"meta\": asd}", "{\"meta\": True}"])
def test_update_budget_invalid_meta(wallet_3hf: Wallet, budget, json_metadata):
    update_budget_time(wallet_3hf, budget)
    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)
    response = wallet_3hf.update_budget(budget['type'], budget['id'], budget['owner'], json_metadata)
    validate_error_response(response, wallet_3hf.update_budget.__name__, RE_PARSE_ERROR)
    budget_obj = wallet_3hf.get_budget(budget['id'], budget['type'])
    assert budget_obj['json_metadata'] == budget["json_metadata"]


@pytest.mark.parametrize('index', [-1, MAX_INT_64])
def test_invalid_idx(wallet_3hf: Wallet, opened_budgets, index):
    validate_error_response(
        wallet_3hf.update_budget(opened_budgets[0]["type"], index, opened_budgets[0]["owner"], "{}"),
        wallet_3hf.update_budget.__name__,
        RE_BUDGET_NOT_EXIST
    )
