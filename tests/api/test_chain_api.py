from src.wallet import Wallet
from tests.common import validate_response


def test_get_chain_capital(wallet: Wallet):
    response = wallet.get_chain_capital()
    assert 'error' not in response, "get_chain_capital operation failed: %s" % response["error"]

    validate_response([
        "active_voters_balancer_scr", "active_voters_balancer_sp", "circulating_capital",
        "circulating_scr", "circulating_sp", "content_balancer_scr",
        "content_reward_fifa_world_cup_2018_bounty_fund_sp_balance", "content_reward_fund_scr_balance",
        "content_reward_fund_sp_balance", "current_witness", "dev_pool_scr_balance", "dev_pool_sp_balance",
        "fund_budget_balance", "head_block_id", ("head_block_number", int), "head_block_time",
        "registration_pool_balance", "total_scorumpower", "total_scr", "total_supply", "total_witness_reward_scr",
        "total_witness_reward_sp", "witness_reward_in_sp_migration_fund"
    ], response)
