from copy import copy

import pytest
from scorum.graphenebase.amount import Amount
from scorum.utils.time import to_date, date_to_str
from tests.common import DEFAULT_WITNESS, apply_hardfork, gen_uid


def update_budget_balance(wallet, budget):
    response = wallet.get_budget(budget['uuid'], budget['type'])
    budget.update(**response)


def empower_advertising_moderator(wallet, account):
    wallet.development_committee_empower_advertising_moderator(DEFAULT_WITNESS, account)
    proposals = wallet.list_proposals()
    wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"])


def update_budget_time(wallet, budget, start=1, deadline=31):
    dgp = wallet.get_dynamic_global_properties()
    budget.update({
        'start': date_to_str(to_date(dgp['time'], tmdelta={'seconds': start})),
        'deadline': date_to_str(to_date(dgp['time'], tmdelta={'seconds': deadline}))
    })


def change_auction_coeffs(wallet, coeffs, budget_type):
    wallet.development_committee_change_budgets_auction_properties(DEFAULT_WITNESS, coeffs, 86400, budget_type)
    proposals = wallet.list_proposals()
    wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"])


def get_per_blocks_count(start, deadline):
    """
    Calculate amount of blocks between budget start and deadline.
    :param int start: Time shift to start budget. Should be > 0. E.g. start_time = head_block_time + start
    :param int deadline: Time shift to close budget. E.g. deadline_time = head_block_time + start + deadline
    :return:
    """
    blocks = deadline // 3 + 1  # deadline == deadline_time - start_time
    if (not start % 3 and deadline % 3) or (start % 3 == 2 and deadline % 3 == 2):
        return blocks + 1
    return blocks


def calc_per_block(per_blocks_cnt: int, balance: Amount):
    per_block = balance / per_blocks_cnt
    reminder = balance - per_block * per_blocks_cnt
    return per_block, reminder


@pytest.fixture(scope="function")
def post_budget():
    return {
        'type': "post",
        'uuid': gen_uid(),
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
        'uuid': gen_uid(),
        'owner': 'test.test1',
        'json_metadata': "{}",
        'balance': "1.000000000 SCR",
        'start': "1970-01-01T00:00:00",
        'deadline': "1970-01-01T00:00:30"
    }


@pytest.fixture(params=['post_budget', 'banner_budget'])
def budget(request):
    return request.getfixturevalue(request.param)


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
        update_budget_time(wallet_3hf, budget_cp, deadline=300)  # to leave all budgets opened
        budget_cp.update({"owner": "test.test%d" % i, 'uuid': gen_uid()})
        wallet_3hf.create_budget(**budget_cp)
        update_budget_balance(wallet_3hf, budget_cp)  # update budget params / set budget id
        budgets.append(budget_cp)
    return budgets


@pytest.fixture(scope="function")
def opened_budgets_same_acc(wallet_3hf, budget):
    budgets = []
    for i in range(1, 4):
        budget_cp = copy(budget)
        update_budget_time(wallet_3hf, budget_cp, deadline=300)  # to leave all budgets opened
        budget_cp.update({'uuid': gen_uid()})
        wallet_3hf.create_budget(**budget_cp)
        update_budget_balance(wallet_3hf, budget_cp)  # update budget params / set budget id
        budgets.append(budget_cp)
    return budgets
