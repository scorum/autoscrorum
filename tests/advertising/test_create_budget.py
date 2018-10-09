from copy import copy

import pytest
from graphenebase.amount import Amount
from src.wallet import Wallet
from tests.advertising.conftest import update_budget_time, update_budget_balance, calc_per_block
from tests.common import (
    validate_response, validate_error_response, check_logs_on_errors, check_virt_ops,
    RE_INSUFF_FUNDS, RE_POSITIVE_BALANCE, RE_DEADLINE_TIME, RE_START_TIME
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


def get_capital_delta(capital_before, capital_after):
    keys = [
        "content_reward_fifa_world_cup_2018_bounty_fund_sp_balance",
        "circulating_capital",
        "content_reward_fund_scr_balance",
        "content_balancer_scr",
        "dev_pool_sp_balance",
        "total_witness_reward_sp",
        "fund_budget_balance",
        "registration_pool_balance",
        "content_reward_fund_sp_balance",
        "witness_reward_in_sp_migration_fund",
        "active_voters_balancer_sp",
        "dev_pool_scr_balance",
        "total_scr",
        "total_witness_reward_scr",
        "total_supply",
        "active_voters_balancer_scr",
        "total_scorumpower"
    ]
    result = {}
    for key in keys:
        delta = Amount(capital_after[key]) - Amount(capital_before[key])
        if delta != 0:
            result[key] = delta
    return result


def check_budgets_distribution(wallet, top_budgets_list):
    capital_before = wallet.get_chain_capital()
    accounts_before = wallet.get_accounts([budget['owner'] for budget in top_budgets_list])
    [update_budget_balance(wallet, b) for b in top_budgets_list]
    accounts_balances_before = {account['name']: account['balance'] for account in accounts_before}

    wallet.get_block(capital_before['head_block_number'] + 1, wait_for_block=True)

    capital_after = wallet.get_chain_capital()
    accounts_after = wallet.get_accounts([budget['owner'] for budget in top_budgets_list])
    [update_budget_balance(wallet, b) for b in top_budgets_list]
    accounts_balances_after = {account['name']: account['balance'] for account in accounts_after}

    capital_delta = get_capital_delta(capital_before, capital_after)
    accounts_balances_delta = {name: Amount(accounts_balances_after[name]) - Amount(accounts_balances_before[name])
                               for name in accounts_balances_after.keys()}

    result = {}
    for budget in top_budgets_list:
        distribution = {}
        distribution['returned_to_owner'] = accounts_balances_delta[budget['owner']]
        distribution['spend'] = Amount(budget['per_block']) - distribution['returned_to_owner']
        distribution['dev_pool'] = distribution['spend'] // 2
        distribution['activity_pool'] = distribution['spend'] - distribution['dev_pool']
        result[budget['id']] = distribution

    total_to_dev_pool = Amount()
    total_to_activity_pool = Amount()
    total_spend = Amount()

    for budget, distr in result.items():
        total_spend += distr['spend']
        total_to_dev_pool += distr['dev_pool']
        total_to_activity_pool += distr['activity_pool']

    assert capital_delta['dev_pool_scr_balance'] == total_to_dev_pool

    assert capital_delta['content_balancer_scr'] + \
           capital_delta['content_reward_fund_scr_balance'] == total_to_activity_pool

    assert capital_delta['dev_pool_scr_balance'] + \
           capital_delta['content_balancer_scr'] + \
           capital_delta['content_reward_fund_scr_balance'] == total_spend

    return result


@pytest.mark.parametrize('start', [0, 6])
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

    per_block, _ = calc_per_block(deadline, budget_balance)
    assert per_block == Amount(budget['per_block'])

    budgets_summary = wallet_3hf.get_dynamic_global_properties()['advertising'][DGP_BUDGETS[budget['type']]]
    assert all(budgets_summary[k] == budget[v] for k, v in DGP_PARAMS_MAP.items())
    node.read_logs()
    check_logs_on_errors(node.logs)


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
    assert len(wallet_3hf.get_budgets(post_budget['owner'], post_budget['type'])) == 1
    assert len(wallet_3hf.get_budgets(banner_budget['owner'], banner_budget['type'])) == 1

    budgets_summary = wallet_3hf.get_dynamic_global_properties()['advertising']
    assert all(
        Amount(budgets_summary[DGP_BUDGETS[b['type']]][k]) == Amount(b[v])
        for k, v in DGP_PARAMS_MAP.items()
        for b in [banner_budget, post_budget]
    )

    update_budget_time(wallet_3hf, new_budget)
    validate_response(wallet_3hf.create_budget(**new_budget), wallet_3hf.create_budget.__name__)
    assert len(wallet_3hf.get_budgets(post_budget['owner'], post_budget['type'])) == 2


def test_create_budgets(wallet_3hf: Wallet, node, opened_budgets_same_acc, budget):
    assert len(wallet_3hf.get_budgets(budget['owner'], budget['type'])) == len(opened_budgets_same_acc)

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
    node.read_logs()
    check_logs_on_errors(node.logs)
