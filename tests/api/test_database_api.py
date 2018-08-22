from src.wallet import Wallet
from tests.common import DEFAULT_WITNESS, validate_response


# TODO: change check of str type to graphenebase.amount.Amount type for any balance, budget, fund, etc. fields


def test_get_account(wallet: Wallet):
    response = wallet.get_account(DEFAULT_WITNESS)
    assert 'error' not in response, "get_account operation failed: %s" % response["error"]
    assert response["name"] == DEFAULT_WITNESS, "Returned invalid account"
    validate_response([
        "active_sp_holders_cashout_time", "active_sp_holders_pending_scr_reward",
        "active_sp_holders_pending_sp_reward"
    ], response)


def test_get_dynamic_global_properties(wallet: Wallet):
    response = wallet.get_dynamic_global_properties()
    assert 'error' not in response, "get_dynamic_global_properties operation failed: %s" % response["error"]
    validate_response([
        ("head_block_number", int), "head_block_id", "current_witness", "total_supply",
        "circulating_capital", "total_scorumpower", "total_pending_balance", "total_pending_scorumpower",
        "total_witness_reward_scr", "total_witness_reward_sp", "majority_version", ("current_aslot", int),
        "recent_slots_filled", ("participation_count", int), ("last_irreversible_block_num", int),
        "registration_pool_balance", "fund_budget_balance", "reward_pool_balance", "max_virtual_bandwidth",
        "content_reward_scr_balance", "content_reward_sp_balance", ("current_reserve_ratio", int)
    ], response)


def test_get_config(wallet: Wallet):
    response = wallet.get_config()
    assert 'error' not in response, "get_dynamic_global_properties operation failed: %s" % response["error"]
    validate_response([
        ("SCORUM_HARDFORK_REQUIRED_WITNESSES", 17), ("SCORUM_MAX_VOTED_WITNESSES", 20),
        ("SCORUM_MAX_WITNESSES", 21)
    ], response)
