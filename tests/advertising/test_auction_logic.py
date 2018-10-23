from copy import copy

import pytest
from scorum.graphenebase.amount import Amount

from automation.wallet import Wallet
from tests.advertising.conftest import update_budget_time, update_budget_balance, change_auction_coeffs
from tests.common import check_virt_ops, gen_uid, DEFAULT_WITNESS


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


def create_budgets(wallet, budget, count, sync_start=False):
    last_block = 0
    delay = 3 if sync_start else 0
    budgets = []
    for i in range(1, count + 1):
        start = delay * (count - i + 1) or 1
        budget_cp = copy(budget)
        update_budget_time(wallet, budget_cp, start=start,  deadline=start + 300 - delay)
        budget_cp.update({
            "owner": "test.test%d" % i,
            'balance': str(Amount(budget['balance']) * i),
            "uuid": gen_uid()
        })
        response = wallet.create_budget(**budget_cp)
        last_block = response['block_num']
        budgets.append(budget_cp)
    return budgets, last_block


def get_sorted_budgets(wallet, budgets, key='per_block'):
    if not budgets:
        return []
    return sorted(
        wallet.get_budgets([b['owner'] for b in budgets], budgets[0]['type']),
        key=lambda x: x[key], reverse=True
    )


INCOME = 'owner_pending_income'
OUTGO = 'budget_pending_outgo'


def get_pending_delta(before, after):
    before_map = {b['uuid']: b for b in before}
    after_map = {a['uuid']: a for a in after}
    delta = dict()
    for k, v in after_map.items():
        if k not in before_map:
            delta[k] = {INCOME: v[INCOME], OUTGO: v[OUTGO], 'per_block': v['per_block']}
        else:
            delta[k] = {
                INCOME: str(Amount(v[INCOME]) - Amount(before_map[k][INCOME])),
                OUTGO: str(Amount(v[OUTGO]) - Amount(before_map[k][OUTGO])),
                'per_block': v['per_block']
            }
    return sorted(delta.values(), key=lambda x: x['per_block'], reverse=True)


def check_budgets_delta_pending_calc(budgets, coeffs):
    # https://github.com/scorum/scorum/blob/v0.3.0/doc/advertising-budget-details.md#how-advertising-auction-works
    def per_block(x):
        return Amount(budgets[x]['per_block'])

    def outgo(x):
        return Amount(budgets[x][OUTGO])

    def income(x):
        return Amount(budgets[x][INCOME])

    n_budgets = len(budgets)
    n_coeffs = len(coeffs)
    n_winners = min(n_budgets, n_coeffs)
    for i in reversed(range(n_winners)):  # e.g. from end to begin
        if i == n_winners - 1 and n_budgets > n_winners:  # last winner, budgets more then winners
            spent = per_block(i + 1)
        elif i == n_winners - 1 and n_budgets == n_winners:  # last winner, budgets eq to winners
            spent = per_block(i)
        else:
            spent = min(outgo(i + 1) + per_block(i + 1) * (coeffs[i] - coeffs[i + 1]) / coeffs[0], per_block(i))

        received = per_block(i) - spent
        assert outgo(i) == spent and income(i) == received, "Incorrect pending calculations: %d %s" % (i, budgets[i])


@pytest.mark.skip_long_term
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
@pytest.mark.skip_long_term
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
    budget_cashout_block = response['block_num'] + adv_cash_blocks + balancer_delay

    wallet_3hf.get_block(response['block_num'] + balancer_delay, wait_for_block=True)

    wallet_3hf.post_comment(**post)
    # post_cashout_block = response['block_num'] + post_cash_blocks

    response = wallet_3hf.vote(DEFAULT_WITNESS, post['author'], post['permlink'])
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


@pytest.mark.parametrize(
    'coeffs, idx, param_stop, param_start',
    [
        # after coeffs reduction last winner became common budget owner
        ([100, 85, 75], -2, OUTGO, INCOME),
        ([100], 1, OUTGO, INCOME),
        # after coeffs extension top common budget owner became last winner
        ([100, 85, 75, 65, 55], -1, INCOME, OUTGO),
        ([90, 75, 65, 55, 35], -1, INCOME, OUTGO)
    ]
)
@pytest.mark.parametrize('sync_start', [True, False])  # to start budgets at same time or not
def test_coeffs_change_influence_on_pending(
        wallet_3hf: Wallet, budget, coeffs, idx, param_stop, param_start, sync_start
):
    budgets, _ = create_budgets(wallet_3hf, budget, 5, sync_start)
    wallet_3hf.development_committee_change_budgets_auction_properties(DEFAULT_WITNESS, coeffs, 86400, budget['type'])
    proposals = wallet_3hf.list_proposals()

    budgets_before = get_sorted_budgets(wallet_3hf, budgets)

    wallet_3hf.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"])

    budgets_after = get_sorted_budgets(wallet_3hf, budgets)

    assert Amount(budgets_after[idx][param_stop]) - Amount(budgets_before[idx][param_stop]) == 0, \
        "Param '%s' shouldn't change after coefficients update." % param_stop
    assert Amount(budgets_after[idx][param_start]) - Amount(budgets_before[idx][param_start]) == \
        Amount(budgets_before[idx]['per_block']), \
        "Param '%s' should increase on per_block amount after coefficients change." % param_start

    check_budgets_delta_pending_calc(get_pending_delta(budgets_before, budgets_after), coeffs)


@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 6])
def test_budget_creation_influence_on_pending(wallet_3hf: Wallet, budget, count):
    coeffs = wallet_3hf.get_auction_coefficients()
    budgets = []
    for i in range(1, count + 1):
        budgets_before = get_sorted_budgets(wallet_3hf, budgets)
        budget_cp = copy(budget)
        update_budget_time(wallet_3hf, budget_cp, start=1, deadline=300)
        budget_cp.update({
            "owner": "test.test%d" % i,
            'balance': str(Amount(budget['balance']) * i),
            'uuid': gen_uid()
        })
        wallet_3hf.create_budget(**budget_cp)
        budgets.append(budget_cp)
        budgets_after = get_sorted_budgets(wallet_3hf, budgets)
        check_budgets_delta_pending_calc(get_pending_delta(budgets_before, budgets_after), coeffs)


def test_single_winner_pending_payments(wallet_3hf: Wallet, budget):
    change_auction_coeffs(wallet_3hf, [100], budget['type'])

    update_budget_time(wallet_3hf, budget, start=3, deadline=300)

    winner = copy(budget)
    winner.update({"owner": "test.test1", 'uuid': gen_uid()})
    potato = copy(budget)  # e.g. not winner (4th place: gold, silver, bronze, potato)
    potato.update({"owner": "test.test2", 'uuid': gen_uid()})
    looser = copy(budget)
    looser.update({"owner": "test.test3", 'uuid': gen_uid(), 'balance': "0.100000000 SCR"})

    budgets = [winner, potato, looser]

    wallet_3hf.broadcast_multiple_ops(
        "create_budget_operation", budgets, {winner['owner'], potato['owner'], looser['owner']}
    )

    [update_budget_balance(wallet_3hf, b) for b in budgets]

    assert winner['per_block'] == potato['per_block']
    assert looser['per_block'] != winner['per_block']
    assert Amount(winner[OUTGO]) == Amount(potato['per_block']) and Amount(winner[INCOME]) == Amount()
    assert Amount(potato[OUTGO]) == Amount() and Amount(potato[INCOME]) == Amount(potato['per_block'])
    assert Amount(looser[OUTGO]) == Amount() and Amount(looser[INCOME]) == Amount(looser['per_block'])
