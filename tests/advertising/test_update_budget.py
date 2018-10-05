import json

import pytest
from src.wallet import Wallet
from graphenebase.amount import Amount
from tests.advertising.conftest import update_budget_time, update_budget_balance
from tests.common import validate_response, validate_error_response, check_virt_ops, RE_PARSE_ERROR, RE_BUDGET_NOT_EXIST


@pytest.mark.parametrize('json_metadata', [json.dumps({"meta": "some_meta"}), "{\"meta\": \"some_meta\"}", "{}"])
def test_update_budget(wallet_3hf: Wallet, budget, json_metadata):
    update_budget_time(budget)
    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)
    response = wallet_3hf.update_budget(budget['type'], budget['id'], budget['owner'], json_metadata)
    validate_response(response, wallet_3hf.update_budget.__name__, [('block_num', int)])
    check_virt_ops(wallet_3hf, response["block_num"], response["block_num"], {'update_budget'})
    budget_obj = wallet_3hf.get_budget(budget['id'], budget['type'])
    assert budget_obj['json_metadata'] == json_metadata
    assert Amount(budget_obj['balance']) == Amount(budget['balance']) - Amount(budget['per_block'])
    for k in set(budget.keys()).difference({"json_metadata", 'balance'}):
        assert budget[k] == budget_obj[k], "Unexpected change of '%s' parameter value." % k


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
    update_budget_time(budget)
    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)
    response = wallet_3hf.update_budget(budget['type'], budget['id'], budget['owner'], json_metadata)
    validate_error_response(response, wallet_3hf.update_budget.__name__, RE_PARSE_ERROR)
    budget_obj = wallet_3hf.get_budget(budget['id'], budget['type'])
    assert budget_obj['json_metadata'] == budget["json_metadata"]


@pytest.mark.parametrize('idx', [10, 999])
def test_update_budget_invalid_idx(wallet_3hf: Wallet, budget, idx):
    response = wallet_3hf.update_budget(budget['type'], idx, budget['owner'], "{}")
    validate_error_response(response, wallet_3hf.update_budget.__name__, RE_BUDGET_NOT_EXIST)

    update_budget_time(budget)
    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)

    response = wallet_3hf.update_budget(budget['type'], 1, budget['owner'], "{}")
    validate_error_response(response, wallet_3hf.update_budget.__name__, RE_BUDGET_NOT_EXIST)
