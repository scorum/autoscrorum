import pytest

from src.utils import to_date
from src.wallet import Wallet
from graphenebase.amount import Amount
from tests.common import DEFAULT_WITNESS, expect, assert_expectations, apply_hardfork


def test_post_comment(wallet: Wallet):
    post_kwargs = {'author': DEFAULT_WITNESS,
                   'permlink': 'initdelegate-post-1',
                   'parent_author': '',
                   'parent_permlink': 'football',
                   'title': 'initdelegate post title',
                   'body': 'initdelegate post body',
                   'json_metadata': '{"tags":["first_tag", "football", "initdelegate_posts"]}'}
    comment_level_1_kwargs = {'author': 'bob',
                              'permlink': 'bob-comment-1',
                              'parent_author': 'initdelegate',
                              'parent_permlink': 'initdelegate-post-1',
                              'title': 'bob comment title',
                              'body': 'bob comment body',
                              'json_metadata': '{"tags":["comment", "initdelegate_posts", "bob_tag"]}'}
    comment_level_2_kwargs = {'author': 'alice',
                              'permlink': 'alice-comment-1',
                              'parent_author': 'bob',
                              'parent_permlink': 'bob-comment-1',
                              'title': 'alice comment title',
                              'body': 'alice comment body',
                              'json_metadata': '{"tags":["comment", "initdelegate_posts", "alice_tag"]}'}

    assert 'error' not in wallet.post_comment(**post_kwargs).keys(), 'post creation failed'
    assert 'error' not in wallet.post_comment(**comment_level_1_kwargs).keys(), 'post creation failed'
    assert 'error' not in wallet.post_comment(**comment_level_2_kwargs).keys(), 'post creation failed'

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

    def validate_comment(comment, comment_kwargs, parent=None):
        print(comment)
        for key, value in comment_kwargs.items():
            assert comment[key] == value, '{} value differs from expected'.format(key)
        assert comment['category'] == post_kwargs['parent_permlink']
        expected_depth = parent['depth'] + 1 if parent else 0
        assert comment['depth'] == expected_depth
        assert comment['root_title'] == post_kwargs['title']
        assert comment['root_comment'] == post['id']
        validate_cashout_interval(comment)
        validate_url(comment)

    post = wallet.get_content(post_kwargs['author'], post_kwargs['permlink'])
    validate_comment(post, post_kwargs)

    comment_level_1 = wallet.get_comments(post_kwargs['author'], post_kwargs['permlink'], 1)
    assert len(comment_level_1) == 1, 'get_content_replies method should return only 1 level children'
    validate_comment(comment_level_1[0], comment_level_1_kwargs, post)

    comment_level_2 = wallet.get_comments(comment_level_1_kwargs['author'], comment_level_1_kwargs['permlink'], 2)[0]
    validate_comment(comment_level_2, comment_level_2_kwargs, comment_level_1[0])


@pytest.mark.long_term
@pytest.mark.parametrize("account", ["alice", "bob"])  # not witness -> we could check balance change
def test_active_sp_holder_reward_single_acc_2hf(wallet: Wallet, account):
    apply_hardfork(wallet, 2)

    post_kwargs = {'author': account,
                   'permlink': 'initdelegate-post-1',
                   'parent_author': '',
                   'parent_permlink': 'football',
                   'title': 'initdelegate post title',
                   'body': 'initdelegate post body',
                   'json_metadata': '{"tags":["first_tag", "football", "initdelegate_posts"]}'}
    assert 'error' not in wallet.post_comment(**post_kwargs).keys(), 'post creation failed'
    assert 'error' not in wallet.vote(account, account, "initdelegate-post-1"), "Vote operation failed"

    account_before = wallet.get_account(account)
    dgp_before = wallet.get_dynamic_global_properties()
    expect(account_before["active_sp_holders_pending_sp_reward"] == dgp_before["total_pending_sp"])

    # 1000000 - microseconds to seconds; 3 seconds to generate one block; ~ 20 blocks for 1 min; 201600 for one week
    reward_period_sec = int(wallet.get_config()["SCORUM_ACTIVE_SP_HOLDERS_REWARD_PERIOD"] / 1000000)
    expected_cashout = to_date(account_before["last_vote_time"], tmdelta={"seconds": reward_period_sec})
    actual_cashout = to_date(account_before["active_sp_holders_cashout_time"])
    expect(expected_cashout == actual_cashout, "Actual cashout time calculated incorrectly.")

    blocks_to_wait = int(reward_period_sec / 3) + 1
    last_block = dgp_before["head_block_number"]
    rewards = []
    for i in range(last_block, last_block + blocks_to_wait):
        wallet.get_block(i, wait_for_block=True)
        ops = wallet.get_ops_in_block(i)
        rewards = [data["op"][1] for _, data in ops if data["op"][0] == "active_sp_holders_reward"]
        if rewards:
            break
    assert len(rewards) == 1, "Should be provided single active_sp_holder_reward payment."
    assert rewards[0]["sp_holder"] == account, "Reward should be payed to specified user."

    account_after = wallet.get_account(account)
    expect(account_before["balance"] == account_after["balance"])  # until advertising is locked
    expect(account_before["scorumpower"] != account_after["scorumpower"])

    reset_cashout = to_date(account_after["active_sp_holders_cashout_time"])
    max_cashout = to_date("1969-12-31T23:59:59")
    expect(reset_cashout == max_cashout, "Cashout time for active_sp_holder_reward was not reset.")

    dgp_after = wallet.get_dynamic_global_properties()
    expect(dgp_before["total_pending_scr"] == dgp_after["total_pending_scr"])  # until advertising is locked
    expect(Amount(dgp_after["total_pending_sp"]) == Amount("0 SP"))
    expect(dgp_before["total_pending_sp"] != dgp_after["total_pending_sp"])
    expect(dgp_before["total_scorumpower"] != dgp_after["total_scorumpower"])

    balance_change = Amount(account_after["scorumpower"]) - Amount(account_before["scorumpower"])
    reward = Amount(rewards[0]["reward"])
    expect(
        balance_change == reward,
        "Balance change is not equal with reward: '%s', expected '%s'" % (balance_change, reward)
    )

    assert_expectations()
