import json

import pytest
from src.wallet import Wallet
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
    assert budget_obj['json_metadata'] != budget["json_metadata"]
    assert budget_obj['json_metadata'] == json_metadata


@pytest.mark.parametrize('json_metadata', ["мама мыла раму", "{\"meta\": asd}", "{\"meta\": True}"])
def test_update_budget_invalid_meta(wallet_3hf: Wallet, budget, json_metadata):
    update_budget_time(budget)
    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)
    response = wallet_3hf.update_budget(budget['type'], budget['id'], budget['owner'], json_metadata)
    validate_error_response(response, wallet_3hf.update_budget.__name__, RE_PARSE_ERROR)
    budget_obj = wallet_3hf.get_budget(budget['id'], budget['type'])
    assert budget_obj['json_metadata'] == budget["json_metadata"]


@pytest.mark.parametrize('idx', [10])
def test_update_budget_invalid_idx(wallet_3hf: Wallet, budget, idx):
    response = wallet_3hf.update_budget(budget['type'], idx, budget['owner'], "{}")
    validate_error_response(response, wallet_3hf.update_budget.__name__, RE_BUDGET_NOT_EXIST)

    update_budget_time(budget)
    wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)

    response = wallet_3hf.update_budget(budget['type'], 1, budget['owner'], "{}")
    validate_error_response(response, wallet_3hf.update_budget.__name__, RE_BUDGET_NOT_EXIST)

