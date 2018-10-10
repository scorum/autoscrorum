from copy import copy

import pytest
from graphenebase.amount import Amount
from src.wallet import Wallet
from tests.advertising.conftest import update_budget_time, update_budget_balance
from tests.common import check_virt_ops, validate_response, DEFAULT_WITNESS


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
        result[key] = Amount(capital_after[key]) - Amount(capital_before[key])
    return result


def get_accounts_delta(accs_after, accs_before):
    return {name: Amount(accs_after[name]) - Amount(accs_before[name]) for name in accs_after.keys()}


def get_affected_balances(wallet, owners):
    capital = wallet.get_chain_capital()
    accounts_balances = {account['name']: account['balance'] for account in wallet.get_accounts(owners)}
    return capital, accounts_balances


def get_total_sums(budgets, accs_delta, blocks_cnt):
    total = {'to_dev_pool': Amount(), 'to_activity_pool': Amount(), 'spend': Amount()}
    for b in budgets:
        spend = Amount(b['per_block']) * blocks_cnt - accs_delta[b['owner']]
        dev_pool = spend // 2
        activity_pool = spend - dev_pool
        total['spend'] += spend
        total['to_dev_pool'] += dev_pool
        total['to_activity_pool'] += activity_pool
    return total


def create_budgets(wallet, budget, count, sync_start):
    last_block = 0
    delay = 3 if sync_start else 0
    budgets = []
    for i in range(1, count + 1):
        start = delay * (count - i + 1) or 1
        budget_cp = copy(budget)
        update_budget_time(wallet, budget_cp, start=start,  deadline=start + 300 - delay)
        budget_cp.update({"owner": "test.test%d" % i, 'balance': str(Amount(budget['balance']) * i)})
        response = wallet.create_budget(**budget_cp)
        validate_response(response, wallet.create_budget.__name__)
        last_block = response['block_num']
        budgets.append(budget_cp)
    return budgets, last_block


@pytest.mark.parametrize('count', [1, 3, 5])
@pytest.mark.parametrize('sync_start', [True, False])  # to start budgets at same time or not
def test_cashout_budgets_distribution(wallet_3hf: Wallet, budget, count, sync_start):
    budgets, last_block = create_budgets(wallet_3hf, budget, count, sync_start)
    owners = [b['owner'] for b in budgets]
    cfg = wallet_3hf.get_config()
    cashout_blocks_cnt = int(cfg["SCORUM_ADVERTISING_CASHOUT_PERIOD_SEC"] / cfg["SCORUM_BLOCK_INTERVAL"])
    # collect data before cashout
    capital_before, accounts_balances_before = get_affected_balances(wallet_3hf, owners)
    [update_budget_balance(wallet_3hf, b) for b in budgets]
    #  wait until cashout
    wallet_3hf.get_block(last_block + cashout_blocks_cnt, wait_for_block=True)
    # collect data after cashout
    capital_after, accounts_balances_after = get_affected_balances(wallet_3hf, owners)
    [update_budget_balance(wallet_3hf, b) for b in budgets]
    # calc delta between 'after', 'before' cashout states
    capital_delta = get_capital_delta(capital_before, capital_after)
    accounts_balances_delta = get_accounts_delta(accounts_balances_after, accounts_balances_before)
    # calc total payments
    total = get_total_sums(budgets, accounts_balances_delta, cashout_blocks_cnt)
    # provide checks
    assert capital_delta['dev_pool_scr_balance'] == total['to_dev_pool']
    assert capital_delta['content_balancer_scr'] + \
        capital_delta['content_reward_fund_scr_balance'] == total['to_activity_pool']
    assert capital_delta['dev_pool_scr_balance'] + \
        capital_delta['content_balancer_scr'] + \
        capital_delta['content_reward_fund_scr_balance'] == total['spend']


# TODO: uncomment blog related lines when cashout time for posts will be decreased. Now it's 7200 sec
def test_cashout_scr_rewards(wallet_3hf: Wallet, budget, post):
    balancer_delay = 7  # blocks to wait until SCR will be in each required pool
    cfg = wallet_3hf.get_config()
    # Advertising cashout_blocks count
    adv_cash_blocks = int(cfg["SCORUM_ADVERTISING_CASHOUT_PERIOD_SEC"] / cfg["SCORUM_BLOCK_INTERVAL"])
    # Post / comment cashout blocks count
    # post_cash_blocks = int(cfg["SCORUM_CASHOUT_WINDOW_SECONDS"] / cfg["SCORUM_BLOCK_INTERVAL"])
    # Active SP holders cashout blocks count
    asph_cash_blocks = int(cfg["SCORUM_ACTIVE_SP_HOLDERS_REWARD_PERIOD"] / 1000000 / cfg["SCORUM_BLOCK_INTERVAL"]) - 1

    update_budget_time(wallet_3hf, budget, deadline=300)
    response = wallet_3hf.create_budget(**budget)
    validate_response(response, wallet_3hf.create_budget.__name__)
    budget_cashout_block = response['block_num'] + adv_cash_blocks + balancer_delay

    wallet_3hf.get_block(response['block_num'] + balancer_delay, wait_for_block=True)

    response = wallet_3hf.post_comment(**post)
    validate_response(response, wallet_3hf.post_comment.__name__)
    # post_cashout_block = response['block_num'] + post_cash_blocks

    response = wallet_3hf.vote(DEFAULT_WITNESS, post['author'], post['permlink'])
    validate_response(response, wallet_3hf.vote.__name__)
    active_sph_cashout_block = response['block_num'] + asph_cash_blocks

    blocks_ops = [
        (budget_cashout_block, 'producer_reward'),
        (active_sph_cashout_block, 'active_sp_holders_reward'),
        # (post_cashout_block, 'author_reward'),
        # (post_cashout_block, 'curator_reward')
    ]
    for cashout_block, op in blocks_ops:
        wallet_3hf.get_block(cashout_block, wait_for_block=True)
        ops = check_virt_ops(wallet_3hf, cashout_block, cashout_block, {op})
        assert any(Amount(data['reward']) > 0 and 'SCR' in data['reward'] for name, data in ops if name == op)
