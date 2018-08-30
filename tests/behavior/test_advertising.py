import pytest

from graphenebase.amount import Amount
from src.genesis import Genesis
from src.utils import fmt_time_from_now
from src.wallet import Wallet
from tests.common import DEFAULT_WITNESS, validate_response


def is_operation_in_block(block, operation_name, operation_kwargs={}):
    for tr in block['transactions']:
        for op in tr['operations']:
            op_name = op[0]
            op_params = op[1]
            if op_name == operation_name:
                if all([op_params[key] == operation_kwargs[key] for key in operation_kwargs.keys()]):
                    return True
    return False


@pytest.mark.parametrize('budget_type', ['banner', 'post'])
def test_create_budget(wallet: Wallet, budget_type):
    budget_kwargs = {'budget_type': budget_type,
                     'owner': DEFAULT_WITNESS,
                     'json_metadata': "{}",
                     'balance': Amount("10.000000000 SCR"),
                     'start': fmt_time_from_now(10),
                     'deadline': fmt_time_from_now(40)}
    balance_before_creation = wallet.get_account_scr_balance(budget_kwargs['owner'])
    result = wallet.create_budget(**budget_kwargs)

    assert "error" not in result, \
        "Could not create budget for '%s', error msg : %s" % (budget_kwargs['owner'], result['error'])

    block = wallet.get_block(result['block_num'])
    assert is_operation_in_block(block, 'create_budget', budget_kwargs), \
        'Operation is not presented in blockchain\n' \
        '{}'.format(block)

    balance_after_creation = wallet.get_account_scr_balance(budget_kwargs['owner'])
    assert balance_before_creation - balance_after_creation == budget_kwargs['balance']

    budgets_list = wallet.get_budgets(budget_kwargs['owner'], budget_kwargs['budget_type'])


def test_create_budget(wallet: Wallet):
    owner = DEFAULT_WITNESS
    response = wallet.create_budget(owner, Amount("10.000000000 SCR"), fmt_time_from_now(10), fmt_time_from_now(40))
    validate_response(response, wallet.create_budget.__name__)

    budget = wallet.get_budgets(owner)[0]
    print(budget)

    per_block_for_10_blocks_budget = Amount('1.000000000 SCR')
    per_block_for_9_blocks_budget = Amount('1.034482758 SCR')

    assert owner in wallet.list_buddget_owners()
    assert Amount(budget['per_block']) in (per_block_for_10_blocks_budget, per_block_for_9_blocks_budget)
    assert budget['owner'] == owner


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
