from copy import copy

import pytest
from scorum.graphenebase.amount import Amount

from automation.wallet import Wallet
from tests.advertising.conftest import update_budget_time, update_budget_balance, calc_per_block, get_per_blocks_count
from tests.common import (
    validate_response, validate_error_response, check_virt_ops, gen_uid,
    RE_INSUFF_FUNDS, RE_POSITIVE_BALANCE, RE_DEADLINE_TIME, RE_START_TIME, RE_MISSING_AUTHORITY, DEFAULT_WITNESS
)

DGP_BUDGETS = {
    "post": "post_budgets",
    "banner": "banner_budgets"
}


DGP_PARAMS_MAP = {
    'volume': 'balance',
    'budget_pending_outgo': 'budget_pending_outgo',
    'owner_pending_income': 'owner_pending_income'
}


@pytest.mark.parametrize('start', [1, 6])
@pytest.mark.parametrize('deadline', [15, 30])
def test_create_budget(wallet_3hf: Wallet, node, budget, start, deadline):
    update_budget_time(wallet_3hf, budget, start=start, deadline=deadline + start)
    budget_balance = Amount(budget["balance"])
    balance_before = wallet_3hf.get_account_scr_balance(budget["owner"])
    response = wallet_3hf.create_budget(**budget)
    validate_response(response, wallet_3hf.create_budget.__name__)
    check_virt_ops(wallet_3hf, response["block_num"], response["block_num"], {'create_budget'})
    balance_after = wallet_3hf.get_account_scr_balance(budget["owner"])
    assert balance_before == balance_after + budget_balance

    update_budget_balance(wallet_3hf, budget)
    assert budget_balance == Amount(budget['balance']) + Amount(budget['owner_pending_income']) + \
        Amount(budget['budget_pending_outgo'])

    per_block, _ = calc_per_block(get_per_blocks_count(start, deadline), budget_balance)
    assert per_block == Amount(budget['per_block'])

    budgets_summary = wallet_3hf.get_dynamic_global_properties()['advertising'][DGP_BUDGETS[budget['type']]]
    assert all(budgets_summary[k] == budget[v] for k, v in DGP_PARAMS_MAP.items())


@pytest.mark.parametrize('params,err_response_code', [
    ({'balance': '99999.000000000 SCR'}, RE_INSUFF_FUNDS),
    ({'balance': '-5.000000000 SCR'}, RE_POSITIVE_BALANCE),
    ({'start': '1999-12-31T00:00:00', 'deadline': '2000-01-01T00:00:00'}, RE_START_TIME),
    ({'start': "2023-01-01T00:00:00", 'deadline': "2022-01-01T00:00:00"}, RE_DEADLINE_TIME)
])
def test_create_budget_invalid_params(wallet_3hf: Wallet, budget, params, err_response_code):
    update_budget_time(wallet_3hf, budget)
    budget.update(params)
    response = wallet_3hf.create_budget(**budget)
    validate_error_response(response, wallet_3hf.create_budget.__name__, err_response_code)


def test_create_post_vs_banner(wallet_3hf: Wallet, post_budget, banner_budget):
    new_budget = copy(post_budget)
    update_budget_time(wallet_3hf, post_budget)
    validate_response(wallet_3hf.create_budget(**post_budget), wallet_3hf.create_budget.__name__)

    update_budget_time(wallet_3hf, banner_budget)
    validate_response(wallet_3hf.create_budget(**banner_budget), wallet_3hf.create_budget.__name__)

    update_budget_balance(wallet_3hf, post_budget)  # update budget params / set budget id
    update_budget_balance(wallet_3hf, banner_budget)  # update budget params / set budget id
    assert post_budget["id"] == banner_budget["id"]  # both = 0
    assert len(wallet_3hf.get_budgets([post_budget['owner']], post_budget['type'])) == 1
    assert len(wallet_3hf.get_budgets([banner_budget['owner']], banner_budget['type'])) == 1

    budgets_summary = wallet_3hf.get_dynamic_global_properties()['advertising']
    assert all(
        Amount(budgets_summary[DGP_BUDGETS[b['type']]][k]) == Amount(b[v])
        for k, v in DGP_PARAMS_MAP.items()
        for b in [banner_budget, post_budget]
    )

    update_budget_time(wallet_3hf, new_budget)
    new_budget.update({'uuid': gen_uid()})
    validate_response(wallet_3hf.create_budget(**new_budget), wallet_3hf.create_budget.__name__)
    assert len(wallet_3hf.get_budgets([post_budget['owner']], post_budget['type'])) == 2


def test_create_budgets(wallet_3hf: Wallet, node, opened_budgets_same_acc, budget):
    assert len(wallet_3hf.get_budgets([budget['owner']], budget['type'])) == len(opened_budgets_same_acc)

    budgets_summary = wallet_3hf.get_dynamic_global_properties()['advertising']

    for b in opened_budgets_same_acc:
        update_budget_balance(wallet_3hf, b)

    # check that sum of budgets 'param' ==  summary 'param' in DGP
    assert all(
        sum([Amount(b[v]) for b in opened_budgets_same_acc], Amount("0 SCR")) == Amount(
            budgets_summary[DGP_BUDGETS[budget['type']]][k]
        )
        for k, v in DGP_PARAMS_MAP.items()
    )


def test_create_max_budgets(wallet_3hf: Wallet, budget):
    re_budgets_limit = r"Can't create more then .* budgets per owner."
    limit = wallet_3hf.get_config()["SCORUM_BUDGETS_LIMIT_PER_OWNER"]
    balance = "0.000000001 SCR"
    update_budget_time(wallet_3hf, budget, start=5, deadline=300)
    budgets = []
    for i in range(1, limit + 1):
        budget_cp = copy(budget)
        budget_cp.update({'uuid': gen_uid(), 'balance': balance})
        budgets.append(budget_cp)
    validate_response(
        wallet_3hf.broadcast_multiple_ops('create_budget_operation', budgets, {budget['owner']}),
        'create_budget_operation'
    )
    update_budget_time(wallet_3hf, budget, start=5, deadline=300)
    validate_error_response(
        wallet_3hf.create_budget(**budget),
        wallet_3hf.create_budget.__name__,
        re_budgets_limit
    )
    wallet_3hf.close_budget(str(budgets[0]['uuid']), budget['owner'], budget['type'])
    update_budget_time(wallet_3hf, budget, start=5, deadline=300)
    validate_response(wallet_3hf.create_budget(**budget), wallet_3hf.create_budget.__name__)


@pytest.mark.parametrize('account', ['alice', DEFAULT_WITNESS, 'test.test2'])
def test_invalid_signing(wallet_3hf: Wallet, budget, account):
    update_budget_time(wallet_3hf, budget)
    validate_error_response(
        wallet_3hf.broadcast_multiple_ops('create_budget_operation', [budget], {account}),
        'create_budget_operation',
        RE_MISSING_AUTHORITY
    )
