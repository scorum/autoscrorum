import pytest
import time

from graphenebase.amount import Amount
from src.genesis import Genesis
from src.utils import fmt_time_from_now
from src.wallet import Wallet
from tests.common import DEFAULT_WITNESS, validate_response


def is_operation_in_block(block, operation_name, operation_kwargs):
    for tr in block['transactions']:
        for op in tr['operations']:
            op_name = op[0]
            op_params = op[1]
            if op_name == operation_name:
                if all([op_params[key] == operation_kwargs[key] for key in operation_kwargs.keys()]):
                    return True
    return False


def find_budget_id(budgets_list, budget_object):
    if 'id' in budget_object.keys():
        return
    for budget in budgets_list:
        if all([budget[key] == budget_object[key] for key in budget_object.keys()]):
            budget_object['id'] = budget['id']
            budget_object['per_block'] = budget['per_block']


def update_budget_balance(wallet, budget_object):
    budgets_list = wallet.get_budgets(budget_object['owner'], budget_object['type'])
    budget_object.pop('balance', None)

    find_budget_id(budgets_list, budget_object)

    for budget in budgets_list:
        if budget['id'] == budget_object['id']:
            budget_object['balance'] = budget['balance']
            budget_object['created'] = budget['created']
            budget_object['json_metadata'] = budget['json_metadata']


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


@pytest.mark.parametrize('budget_type', ['banner', 'post'])
def test_create_budget(wallet: Wallet, budget_type):
    budget_kwargs = {'type': budget_type,
                     'owner': 'test.test1',
                     'json_metadata': "{}",
                     'balance': "1.000000000 SCR",
                     'start': fmt_time_from_now(0),
                     'deadline': fmt_time_from_now(30)}
    balance_before_creation = wallet.get_account_scr_balance(budget_kwargs['owner'])
    response = wallet.create_budget(**budget_kwargs)

    validate_response(response, wallet.create_budget.__name__)

    block = wallet.get_block(response['block_num'])
    assert is_operation_in_block(block, 'create_budget', budget_kwargs), \
        'Operation is not presented in blockchain\n' \
        '{}'.format(block)

    balance_after_creation = wallet.get_account_scr_balance(budget_kwargs['owner'])
    assert balance_before_creation - balance_after_creation == Amount(budget_kwargs['balance'])

    update_budget_balance(wallet, budget_kwargs)
    assert 'id' in budget_kwargs.keys(), \
        'Budget is not returned by get_budgets operation'

    check_budgets_distribution(wallet, [budget_kwargs])


@pytest.mark.parametrize('budget_type', ['banner', 'post'])
def test_close_budget(wallet: Wallet, budget_type):
    budget_kwargs = {'type': budget_type,
                     'owner': 'test.test1',
                     'json_metadata': "{}",
                     'balance': "1.000000000 SCR",
                     'start': fmt_time_from_now(0),
                     'deadline': fmt_time_from_now(30)}
    response = wallet.create_budget(**budget_kwargs)
    wallet.get_block(response['block_num']+1, wait_for_block=True)

    update_budget_balance(wallet, budget_kwargs)
    balance_before_close = wallet.get_account_scr_balance(budget_kwargs['owner'])

    response = wallet.close_budget(budget_kwargs['type'], budget_kwargs['id'], budget_kwargs['owner'])
    validate_response(response, wallet.close_budget.__name__)

    balance_after_close = wallet.get_account_scr_balance(budget_kwargs['owner'])

    assert balance_after_close - balance_before_close == Amount(budget_kwargs['balance'])
    assert len(wallet.get_budgets(budget_kwargs['owner'], budget_kwargs['type'])) == 0
    assert len(wallet.list_buddget_owners(budget_type=budget_kwargs['type'])) == 0


@pytest.mark.parametrize('budget_type', ['banner', 'post'])
def test_update_budget(wallet: Wallet, budget_type):
    budget_kwargs = {'type': budget_type,
                     'owner': 'test.test1',
                     'json_metadata': '{"key": "value"}',
                     'balance': "1.000000000 SCR",
                     'start': fmt_time_from_now(0),
                     'deadline': fmt_time_from_now(30)}
    wallet.create_budget(**budget_kwargs)
    update_budget_balance(wallet, budget_kwargs)

    update_budget_kwargs = {'type': budget_kwargs['type'],
                            'budget_id': budget_kwargs['id'],
                            'owner': budget_kwargs['owner'],
                            'json_metadata': '{"updated_key": "updated_value"}'}
    response = wallet.update_budget(**update_budget_kwargs)
    validate_response(response, wallet.update_budget.__name__)

    budget = wallet.get_budgets(owner_name=budget_kwargs['owner'], budget_type=budget_kwargs['type'])[0]

    assert is_operation_in_block(wallet.get_block(response['block_num']), 'update_budget', update_budget_kwargs)
    assert budget['json_metadata'] == update_budget_kwargs['json_metadata']

    update_budget_balance(wallet, budget_kwargs)
    assert all(budget_kwargs[key] == budget[key] for key in budget_kwargs.keys()),\
        'Not only budget metadata changed after update\n' \
        'before: {}\n' \
        'after: {}'.format(budget_kwargs, budget)


def test_get_current_winners(wallet: Wallet):
    pass



# def test_config_genesis_keys(genesis: Genesis, config: Config, wallet: Wallet):



# def test_create_budget(wallet: Wallet):
#     owner = DEFAULT_WITNESS
#     response = wallet.create_budget(owner, Amount("10.000000000 SCR"), fmt_time_from_now(10), fmt_time_from_now(40))
#     validate_response(response, wallet.create_budget.__name__)
#
#     budget = wallet.get_budgets(owner)[0]
#     print(budget)
#
#     per_block_for_10_blocks_budget = Amount('1.000000000 SCR')
#     per_block_for_9_blocks_budget = Amount('1.034482758 SCR')
#
#     assert owner in wallet.list_buddget_owners()
#     assert Amount(budget['per_block']) in (per_block_for_10_blocks_budget, per_block_for_9_blocks_budget)
#     assert budget['owner'] == owner


@pytest.mark.xfail(reason='BLOC-207')
@pytest.mark.parametrize('genesis', ({'rewards_supply': '0.420480000 SCR'},), indirect=True)
def test_budget_impact_on_rewards(wallet: Wallet, genesis: Genesis):
    def get_reward_per_block():
        last_confirmed_block = wallet.get_witness(DEFAULT_WITNESS)['last_confirmed_block_num']
        sp_balance_before_block_confirm = wallet.get_account_sp_balance(DEFAULT_WITNESS)
        circulating_capital_before = wallet.get_circulating_capital()

        new_confirmed_block = last_confirmed_block
        while new_confirmed_block == last_confirmed_block:
            new_confirmed_block = wallet.get_witness(DEFAULT_WITNESS)['last_confirmed_block_num']

        witness_reward = wallet.get_account_sp_balance(DEFAULT_WITNESS) - sp_balance_before_block_confirm
        full_content_reward = wallet.get_circulating_capital() - circulating_capital_before

        activity_content_reward = full_content_reward * 95 / 100
        assert witness_reward == full_content_reward - activity_content_reward, 'witness reward per block != expected'
        return full_content_reward

    def calculate_rewards_from_genesis():
        blocks_per_month = 864000
        days_in_month = 30
        days_in_2_years = 730
        rewards_supply = Amount(genesis['rewards_supply'])
        rewards_per_block = rewards_supply * days_in_month / days_in_2_years / blocks_per_month
        return rewards_per_block

    '''
    content reward before balancer decrease it
    '''
    expected_content_reward_on_start = calculate_rewards_from_genesis()
    content_reward_on_start = get_reward_per_block()
    assert expected_content_reward_on_start == content_reward_on_start, 'content reward on start != expected'

    '''
    wait for balancer decrease content reward
    '''
    wallet.get_block(25, wait_for_block=True, time_to_wait=60)

    content_reward_after_balancer_decrease = get_reward_per_block()
    assert content_reward_after_balancer_decrease < content_reward_on_start, 'content reward not decreased by balancer'

    '''
    open budget with large amount and short lifetime to instantly increase reward pool which enforce balancer to
    increase content reward
    '''
    wallet.create_budget(DEFAULT_WITNESS, Amount("10000.000000000 SCR"), fmt_time_from_now(), fmt_time_from_now(30))

    content_reward_after_budget_open = get_reward_per_block()
    assert content_reward_after_budget_open > content_reward_after_balancer_decrease, \
        'content reward not increased after budget open'


def empower_advertising_moderator(wallet, account):
    validate_response(
        wallet.development_committee_empower_advertising_moderator(DEFAULT_WITNESS, account),
        wallet.development_committee_empower_advertising_moderator.__name__
    )

    proposals = wallet.list_proposals()
    validate_response(proposals, wallet.list_proposals.__name__)
    assert len(proposals) == 1, "Was created %d proposals, expected only one: %s" % (len(proposals), proposals)

    validate_response(wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"]), wallet.proposal_vote.__name__)


def update_budget_time(budget, start=0, deadline=30):
    budget.update({
        'start': fmt_time_from_now(start),
        'deadline': fmt_time_from_now(deadline)
    })


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_budget_by_moderator_before_starttime(wallet: Wallet, budget, moderator):
    update_budget_time(budget, start=30)
    budget_balance = Amount(budget["balance"])
    balance_before = wallet.get_account_scr_balance(budget["owner"])

    validate_response(wallet.create_budget(**budget), wallet.create_budget.__name__)
    update_budget_balance(wallet, budget)  # update budget params / set budget id

    balance_after_create = wallet.get_account_scr_balance(budget["owner"])

    assert balance_before - balance_after_create == budget_balance

    empower_advertising_moderator(wallet, moderator)
    response = wallet.close_budget_by_advertising_moderator(moderator, budget["id"], budget["type"])
    validate_response(response, wallet.close_budget_by_advertising_moderator.__name__)

    balance_after_close = wallet.get_account_scr_balance(budget["owner"])
    assert balance_after_close == balance_after_create + budget_balance


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_budget_by_moderator_after_starttime(wallet: Wallet, budget, moderator):
    update_budget_time(budget)
    budget_balance = Amount(budget["balance"])
    balance_before = wallet.get_account_scr_balance(budget["owner"])

    response = wallet.create_budget(**budget)
    validate_response(response, wallet.create_budget.__name__)
    create_block = response["block_num"]
    update_budget_balance(wallet, budget)  # update budget params / set budget id
    per_block = Amount(budget["per_block"])

    balance_after_create = wallet.get_account_scr_balance(budget["owner"])

    assert balance_before - balance_after_create == budget_balance

    empower_advertising_moderator(wallet, moderator)
    response = wallet.close_budget_by_advertising_moderator(moderator, budget["id"], budget["type"])
    validate_response(response, wallet.close_budget_by_advertising_moderator.__name__)
    close_block = response["block_num"]

    balance_after_close = wallet.get_account_scr_balance(budget["owner"])
    assert balance_after_close == balance_after_create + budget_balance - per_block * (close_block - create_block)


@pytest.mark.parametrize('moderator', ['alice', 'bob'])
def test_close_budget_by_moderator_post_vs_banner(wallet: Wallet, moderator, post_budget, banner_budget):
    update_budget_time(post_budget)
    validate_response(wallet.create_budget(**post_budget), wallet.create_budget.__name__)
    update_budget_balance(wallet, post_budget)  # update budget params / set budget id

    update_budget_time(banner_budget)
    validate_response(wallet.create_budget(**banner_budget), wallet.create_budget.__name__)
    update_budget_balance(wallet, banner_budget)  # update budget params / set budget id

    assert post_budget["id"] == banner_budget["id"]  # both = 0

    empower_advertising_moderator(wallet, moderator)
    response = wallet.close_budget_by_advertising_moderator(moderator, post_budget["id"], post_budget["type"])
    validate_response(response, wallet.close_budget_by_advertising_moderator.__name__)

    banner_budgets = wallet.get_budgets(banner_budget['owner'], banner_budget['type'])
    assert len(banner_budgets) == 1
