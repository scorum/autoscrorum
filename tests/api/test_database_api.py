from src.wallet import Wallet
from tests.common import DEFAULT_WITNESS, validate_response


# TODO: change check of str type to graphenebase.amount.Amount type for any balance, budget, fund, etc. fields


def test_get_block(wallet: Wallet):
    validate_response(wallet.get_block(1, wait_for_block=True), wallet.get_block.__name__)


def test_get_account(wallet: Wallet):
    response = wallet.get_account(DEFAULT_WITNESS)
    validate_response(response, wallet.get_account.__name__, [
        "active_sp_holders_cashout_time", "active_sp_holders_pending_scr_reward",
        "active_sp_holders_pending_sp_reward", "balance", "scorumpower", "name", "created",
        "last_root_post", "received_scorumpower", ("can_vote", bool), ("created_by_genesis", bool),
        "curation_rewards_sp", "curation_rewards_scr", ("voting_power", int), ("post_count", int),
        "posting_rewards_sp", "posting_rewards_scr", "delegated_scorumpower", "memo_key",
        "last_vote_time", "last_post"
    ])
    assert response["name"] == DEFAULT_WITNESS, "Returned invalid account"


def test_get_dynamic_global_properties(wallet: Wallet):
    response = wallet.get_dynamic_global_properties()
    validate_response(response, wallet.get_dynamic_global_properties.__name__, [
        ("head_block_number", int), "head_block_id", "current_witness", "total_supply",
        "circulating_capital", "total_scorumpower", "total_pending_scr", "total_pending_sp",
        "total_witness_reward_scr", "total_witness_reward_sp", "majority_version", ("current_aslot", int),
        "recent_slots_filled", ("participation_count", int), ("last_irreversible_block_num", int),
        "registration_pool_balance", "fund_budget_balance", "reward_pool_balance", "max_virtual_bandwidth",
        "content_reward_scr_balance", "content_reward_sp_balance", ("current_reserve_ratio", int),
        ("advertising", dict)
    ])


def test_get_config(wallet: Wallet):
    response = wallet.get_config()
    validate_response(response, wallet.get_config.__name__, [
        ("SCORUM_HARDFORK_REQUIRED_WITNESSES", 17), ("SCORUM_MAX_VOTED_WITNESSES", 20),
        ("SCORUM_MAX_WITNESSES", 21),  # ("SCORUM_ACTIVE_SP_HOLDERS_REWARD_PERIOD", int), due to BLOC-484
        ("SCORUM_ACTIVE_SP_HOLDERS_PER_BLOCK_REWARD_PERCENT", int),
        ("SCORUM_VESTING_WITHDRAW_INTERVALS", 52), ("SCORUM_VESTING_WITHDRAW_INTERVAL_SECONDS", int),
        ("SCORUM_LOW_MEMORY_NODE", bool), ("SCORUM_CLEAR_VOTES", bool), ("SCORUM_SKIP_BY_TX_ID", bool),
        ("SCORUM_LIVE_TESTNET", bool), ("SCORUM_ADVERTISING_CASHOUT_PERIOD_SEC", int),
        ("SCORUM_BUDGETS_LIMIT_PER_OWNER", 100)
    ])
