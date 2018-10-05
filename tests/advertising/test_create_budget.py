from copy import copy

import pytest
from graphenebase.amount import Amount
from src.utils import fmt_time_from_now
from src.wallet import Wallet
from tests.advertising.conftest import update_budget_time, update_budget_balance
from tests.common import (
    validate_response, validate_error_response, check_logs_on_errors, check_virt_ops,
    RE_BUDGET_NOT_EXIST, MAX_INT_64
)

DGP_BUDGETS = {
    "post": "post_budgets",
    "banner": "banner_budgets"
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
def test_create_budget(wallet_3hf: Wallet, budget, start):
    update_budget_time(budget, start=start, deadline=start + 30)
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

    budgets_summary = wallet_3hf.get_dynamic_global_properties()['advertising'][DGP_BUDGETS[budget['type']]]
    assert budgets_summary['volume'] == budget['balance']
    assert budgets_summary['budget_pending_outgo'] == budget['budget_pending_outgo']
    assert budgets_summary['owner_pending_income'] == budget['owner_pending_income']
