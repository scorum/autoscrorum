import pytest
from graphenebase.amount import Amount
from src.wallet import Wallet
from src.utils import fmt_time_from_now
from tests.common import validate_response, check_logs_on_errors
from tests.advertising.conftest import update_budget_time, update_budget_balance


@pytest.mark.parametrize('start', [0, 6])
@pytest.mark.parametrize('deadline', [6, 7, 14, 18, 21])
@pytest.mark.parametrize('balance', ["1.000000000 SCR", "0.000000001 SCR", "0.000000015 SCR"])
def test_deadline_close_budget(wallet_3hf: Wallet, budget, start, deadline, node, balance):
    acc_balance_before = wallet_3hf.get_account_scr_balance(budget['owner'])
    update_budget_time(budget, start=start, deadline=start+deadline)
    budget.update({"balance": balance})
    response = wallet_3hf.create_budget(**budget)
    update_budget_balance(wallet_3hf, budget)
    validate_response(response, wallet_3hf.create_budget.__name__, [('block_num', int)])
    last_block = response['block_num']

    blocks_wait = last_block + (deadline + start) // 3
    wallet_3hf.get_block(blocks_wait + 1, wait_for_block=True)
    budgets = wallet_3hf.get_user_budgets(budget['owner'])
    validate_response(budgets, wallet_3hf.get_user_budgets.__name__)
    assert 0 == len(budgets), "All budgets should be closed. %s" % fmt_time_from_now()
    acc_balance_after = wallet_3hf.get_account_scr_balance(budget['owner'])
    assert acc_balance_before - Amount(balance) == acc_balance_after
    ops = set()
    for i in range(blocks_wait - 1, blocks_wait + 2):
        ops.update(set(data['op'][0] for _, data in wallet_3hf.get_ops_in_block(i)))
    expected_ops = {'allocate_cash_from_advertising_budget', 'closing_budget'}
    assert len(ops.intersection(expected_ops)) == len(expected_ops), "Some expected virtual operations are misssing."
    node.read_logs()
    check_logs_on_errors(node.logs)
