from copy import copy

import pytest
from src.utils import fmt_time_from_now
from tests.common import DEFAULT_WITNESS, validate_response, apply_hardfork


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


@pytest.fixture(scope="function")
def post_budget():
    return {
        'type': "post",
        'owner': 'test.test1',
        'json_metadata': "{}",
        'balance': "1.000000000 SCR",
        'start': "1970-01-01T00:00:00",
        'deadline': "1970-01-01T00:00:30"
    }


@pytest.fixture(scope="function")
def banner_budget():
    return {
        'type': "banner",
        'owner': 'test.test1',
        'json_metadata': "{}",
        'balance': "1.000000000 SCR",
        'start': "1970-01-01T00:00:00",
        'deadline': "1970-01-01T00:00:30"
    }


@pytest.fixture(params=['post_budget'])
def budget(request):
    return request.getfuncargvalue(request.param)


@pytest.fixture(scope="function")
def budgets(post_budget, banner_budget):
    return [post_budget, banner_budget]


@pytest.fixture(scope="function")
def wallet_3hf(wallet):
    apply_hardfork(wallet, 3)
    return wallet


@pytest.fixture(scope="function")
def opened_budgets(wallet_3hf, budget):
    budgets = []
    for i in range(1, 4):
        budget_cp = copy(budget)
        update_budget_time(budget_cp, deadline=300)  # to leave all budgets opened
        budget_cp.update({"owner": "test.test%d" % i})
        validate_response(wallet_3hf.create_budget(**budget_cp), wallet_3hf.create_budget.__name__)
        update_budget_balance(wallet_3hf, budget_cp)  # update budget params / set budget id
        budgets.append(budget_cp)
    return budgets


@pytest.fixture(scope="function")
def opened_budgets_same_acc(wallet_3hf, budget):
    budgets = []
    for i in range(1, 4):
        budget_cp = copy(budget)
        update_budget_time(budget_cp, deadline=300)  # to leave all budgets opened
        validate_response(wallet_3hf.create_budget(**budget_cp), wallet_3hf.create_budget.__name__)
        update_budget_balance(wallet_3hf, budget_cp)  # update budget params / set budget id
        budgets.append(budget_cp)
    return budgets
