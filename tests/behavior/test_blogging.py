import pytest

from graphenebase.amount import Amount
from src.utils import to_date, date_to_str
from src.wallet import Wallet
from tests.common import (
    DEFAULT_WITNESS, expect, assert_expectations, apply_hardfork, validate_response, validate_error_response
)
from tests.data import post_with_multilvl_comments, initdelegate_post, bob_comment_lv1, alice_comment_lv2


def test_validate_get_content(wallet: Wallet):
    for post in post_with_multilvl_comments:
        validate_response(wallet.post_comment(**post), wallet.post_comment.__name__)

    time_config = wallet.get_config()

    def validate_cashout_interval(comment: dict):
        date_start = to_date(comment['created'])
        date_finish = to_date(comment['cashout_time'])
        delta = date_finish - date_start
        cashout_window = int(time_config["SCORUM_CASHOUT_WINDOW_SECONDS"])
        assert delta.total_seconds() == cashout_window

    def validate_url(comment: dict):
        if comment['parent_author']:
            assert comment['url'] == '/{category}/@{root_author}/{root_permlink}#@{author}/{permlink}' \
                .format(category=comment['category'],
                        root_author=post['author'],
                        root_permlink=post['permlink'],
                        author=comment['author'],
                        permlink=comment['permlink'])
        else:
            assert comment['url'] == '/{}/@{}/{}'.format(comment['category'], comment['author'], comment['permlink'])

    def validate_content(comment, comment_kwargs, parent=None):
        for key, value in comment_kwargs.items():
            assert comment[key] == value, '{} value differs from expected'.format(key)
        assert comment['category'] == initdelegate_post['parent_permlink']
        expected_depth = parent['depth'] + 1 if parent else 0
        assert comment['depth'] == expected_depth
        assert comment['root_title'] == initdelegate_post['title']
        assert comment['root_comment'] == post['id']
        validate_cashout_interval(comment)
        validate_url(comment)

    post = wallet.get_content(initdelegate_post['author'], initdelegate_post['permlink'])
    validate_content(post, initdelegate_post)

    comment_level_1 = wallet.get_content(bob_comment_lv1['author'], bob_comment_lv1['permlink'])
    validate_content(comment_level_1, bob_comment_lv1, post)

    comment_level_2 = wallet.get_content(alice_comment_lv2['author'], alice_comment_lv2['permlink'])
    validate_content(comment_level_2, alice_comment_lv2, comment_level_1)


@pytest.mark.parametrize("account", [DEFAULT_WITNESS, "alice", "bob"])
def test_vote_operation(wallet: Wallet, account):
    post_kwargs = {'author': account,
                   'permlink': 'initdelegate-post-1',
                   'parent_author': '',
                   'parent_permlink': 'football',
                   'title': 'initdelegate post title',
                   'body': 'initdelegate post body',
                   'json_metadata': '{"tags":["first_tag", "football", "initdelegate_posts"]}'}
    validate_response(wallet.post_comment(**post_kwargs), wallet.post_comment.__name__)

    validate_response(wallet.vote(account, account, "initdelegate-post-1"), wallet.vote.__name__)
    validate_response(wallet.vote(account, account, "initdelegate-post-1", weight=-100), wallet.vote.__name__)

    validate_error_response(wallet.vote(account, account, "initdelegate-post-1", weight=1000), wallet.vote.__name__)
    validate_error_response(wallet.vote(account, account, "initdelegate-post-1", weight=-1000), wallet.vote.__name__)


@pytest.mark.parametrize("account", [DEFAULT_WITNESS, "alice", "bob"])
def test_vote_operation_2hf(wallet: Wallet, account):
    apply_hardfork(wallet, 2)

    post_kwargs = {'author': account,
                   'permlink': 'initdelegate-post-1',
                   'parent_author': '',
                   'parent_permlink': 'football',
                   'title': 'initdelegate post title',
                   'body': 'initdelegate post body',
                   'json_metadata': '{"tags":["first_tag", "football", "initdelegate_posts"]}'}
    validate_response(wallet.post_comment(**post_kwargs), wallet.post_comment.__name__)

    validate_response(wallet.vote(account, account, "initdelegate-post-1"), wallet.vote.__name__)
    validate_response(wallet.vote(account, account, "initdelegate-post-1", weight=-100), wallet.vote.__name__)
    validate_response(wallet.vote(account, account, "initdelegate-post-1", weight=-1000), wallet.vote.__name__)
    validate_response(wallet.vote(account, account, "initdelegate-post-1", weight=10000), wallet.vote.__name__)

    validate_error_response(wallet.vote(account, account, "initdelegate-post-1", weight=11111), wallet.vote.__name__)
    validate_error_response(wallet.vote(account, account, "initdelegate-post-1", weight=-10001), wallet.vote.__name__)


@pytest.mark.skip_long_term
@pytest.mark.parametrize("account", ["alice", "bob"])  # not witness -> we could check balance change
def test_active_sp_holder_reward_single_acc_2hf(wallet: Wallet, account):

    def check_reward_operation(start, stop):
        rewards = []
        for i in range(start, stop):
            wallet.get_block(i, wait_for_block=True)
            ops = wallet.get_ops_in_block(i)
            rewards = [data["op"][1] for _, data in ops if data["op"][0] == "active_sp_holders_reward"]
            if rewards:
                break
        assert len(rewards) == 1, "Should be provided single active_sp_holder_reward payment."
        assert rewards[0]["sp_holder"] == account, "Reward should be payed to specified user."
        return Amount(rewards[0]["reward"])

    apply_hardfork(wallet, 2)

    post_kwargs = {'author': account,
                   'permlink': 'initdelegate-post-1',
                   'parent_author': '',
                   'parent_permlink': 'football',
                   'title': 'initdelegate post title',
                   'body': 'initdelegate post body',
                   'json_metadata': '{"tags":["first_tag", "football", "initdelegate_posts"]}'}
    validate_response(wallet.post_comment(**post_kwargs), wallet.post_comment.__name__)
    validate_response(wallet.vote(account, account, "initdelegate-post-1"), wallet.vote.__name__)

    account_before = wallet.get_account(account)
    dgp_before = wallet.get_dynamic_global_properties()
    expect(account_before["active_sp_holders_pending_sp_reward"] == dgp_before["total_pending_sp"])

    # 1000000 - microseconds to seconds; 3 seconds to generate one block; ~ 20 blocks for 1 min; 201600 for one week
    reward_period_sec = int(wallet.get_config()["SCORUM_ACTIVE_SP_HOLDERS_REWARD_PERIOD"] / 1000000)
    expected_cashout = to_date(account_before["last_vote_time"], tmdelta={"seconds": reward_period_sec})
    actual_cashout = to_date(account_before["active_sp_holders_cashout_time"])
    expect(
        actual_cashout == expected_cashout,
        "Actual cashout time calculated incorrectly: '%s', expected '%s'" %
        (date_to_str(actual_cashout), date_to_str(expected_cashout))
    )

    blocks_to_wait = int(reward_period_sec / 3) + 1
    last_block = dgp_before["head_block_number"]
    reward = check_reward_operation(last_block, last_block + blocks_to_wait)

    account_after = wallet.get_account(account)
    expect(account_before["balance"] == account_after["balance"])  # until advertising is locked
    expect(account_before["scorumpower"] != account_after["scorumpower"])

    reset_cashout = to_date(account_after["active_sp_holders_cashout_time"])
    expected_cashout = to_date(account_before["active_sp_holders_cashout_time"], tmdelta={"seconds": reward_period_sec})
    expect(
        reset_cashout == expected_cashout,
        "Cashout time for active_sp_holder_reward was not reset: '%s', expected '%s'" %
        (date_to_str(reset_cashout), date_to_str(expected_cashout))
    )

    dgp_after = wallet.get_dynamic_global_properties()
    expect(dgp_before["total_pending_scr"] == dgp_after["total_pending_scr"])  # until advertising is locked
    expect(Amount(dgp_after["total_pending_sp"]) == Amount("0 SP"))
    expect(dgp_before["total_pending_sp"] != dgp_after["total_pending_sp"])
    expect(dgp_before["total_scorumpower"] != dgp_after["total_scorumpower"])

    balance_change = Amount(account_after["scorumpower"]) - Amount(account_before["scorumpower"])
    expect(
        balance_change == reward,
        "Balance change is not equal with reward: '%s', expected '%s'" % (balance_change, reward)
    )

    assert_expectations()

    last_block = dgp_after["head_block_number"]
    check_reward_operation(last_block + 1, last_block + blocks_to_wait)
