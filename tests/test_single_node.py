import datetime

import pytest

from autoscorum.account import Account
from autoscorum.config import Config
from autoscorum.docker_controller import DockerController
from autoscorum.errors import Errors
from autoscorum.genesis import Genesis
from autoscorum.node import Node
from autoscorum.utils import fmt_time_from_now
from autoscorum.wallet import Wallet
from graphenebase.amount import Amount
from tests.common import (
    generate_blocks, check_logs_on_errors, check_file_creation
)
from tests.conftest import DEFAULT_WITNESS


def test_block_production(wallet: Wallet, node: Node):
    block = wallet.get_block(1)

    assert block['witness'] == node.config['witness'][1:-1]


def test_genesis_block(wallet: Wallet, genesis: Genesis):
    info = wallet.get_dynamic_global_properties()

    records = [
        'accounts_supply', 'rewards_supply', 'registration_supply',
        'founders_supply', 'steemit_bounty_accounts_supply',
        'development_sp_supply', 'development_scr_supply'
    ]

    expected_total_supply = Amount()

    for r in records:
        expected_total_supply = expected_total_supply + Amount(genesis[r])

    assert Amount(info['total_supply']) == expected_total_supply

    for account, amount in genesis.genesis_accounts:
        assert wallet.get_account_scr_balance(account.name) == amount


def test_node_logs(node, wallet):
    """
    Check logs of running node (logs are created, updated, there are no errors).

    :param Node node: Running node
    :param Wallet wallet: Wallet client to communicate with node
    """
    check_file_creation(node.logs_path)
    prev_size = 0
    for i in range(1, 5):  # or any max number of blocks
        wallet.get_block(i, wait_for_block=True)
        node.read_logs()
        curr_size = len(node.logs)
        assert curr_size > prev_size, "Node logs are not updated."
        prev_size = curr_size
        check_logs_on_errors(node.logs)


def test_transfer(wallet: Wallet):
    initdelegate_balance_before = wallet.get_account_scr_balance('initdelegate')
    amount = initdelegate_balance_before - Amount('5.000000000 SCR')
    alice_balance_before = wallet.get_account_scr_balance('alice')

    print(wallet.transfer('initdelegate', 'alice', amount))

    initdelegate_balance_after = wallet.get_account_scr_balance('initdelegate')
    alice_balance_after = wallet.get_account_scr_balance('alice')

    assert initdelegate_balance_after == initdelegate_balance_before - amount
    assert alice_balance_after == alice_balance_before + amount


def test_transfer_invalid_amount(wallet: Wallet):
    initdelegate_balance_before = wallet.get_account_scr_balance('initdelegate')
    amount = initdelegate_balance_before + Amount('0.000000001 SCR')
    alice_balance_before = wallet.get_account_scr_balance('alice')

    response = wallet.transfer('initdelegate', 'alice', amount)

    initdelegate_balance_after = wallet.get_account_scr_balance('initdelegate')
    alice_balance_after = wallet.get_account_scr_balance('alice')

    assert initdelegate_balance_after == initdelegate_balance_before
    assert alice_balance_after == alice_balance_before

    assert 'Account does not have sufficient funds for transfer' in response['error']['message']


def test_transfer_to_vesting(wallet: Wallet):
    initdelegate_scr_balance_before = wallet.get_account_scr_balance('initdelegate')
    alice_sp_balance_before = wallet.get_account_sp_balance('alice')

    amount = Amount('1.000000000 SCR')

    wallet.transfer_to_scorumpower('initdelegate', 'alice', amount)

    initdelegate_scr_balance_after = wallet.get_account_scr_balance('initdelegate')
    alice_sp_balance_after = wallet.get_account_sp_balance('alice')

    assert initdelegate_scr_balance_after == initdelegate_scr_balance_before - amount
    assert alice_sp_balance_after == alice_sp_balance_before + amount


test_account_memo_key = 'SCR52jUWZchsz6hVD13PzZrQP94mcbJL5seYxnm46Uk6D9tmJdGJh'
test_account_owner_pub_key = 'SCR695t7HG9WMA2HnZkPGnjQkBDXza1WQLKhztdhrN9VwqMJr3WK4'
test_accout_posting_pub_key = 'SCR8eP1ZeZGJxQNK7sRzbS5TMpmDHj6iKtNdLP2AfwV3tfq8ch1R6'
test_account_active_pub_key = 'SCR8G7CU317DiQxkq95c5poDV74nu715CbU8h3QqoNy2Rzv9wFGnj'


@pytest.mark.parametrize('valid_name', ['joe', 'ahahahahahahaha1'])
def test_create_account(wallet: Wallet, valid_name):
    fee = Amount('0.000001000 SCR')
    account_before = wallet.list_accounts()

    creator_balance_before = wallet.get_account_scr_balance(DEFAULT_WITNESS)
    print(wallet.create_account(DEFAULT_WITNESS,
                                newname=valid_name,
                                owner=test_account_owner_pub_key,
                                active=test_account_active_pub_key,
                                posting=test_accout_posting_pub_key,
                                memo=test_account_memo_key,
                                fee=fee))
    creator_balance_delta = creator_balance_before - wallet.get_account_scr_balance(DEFAULT_WITNESS)
    assert creator_balance_delta == fee

    assert wallet.get_account(valid_name)['recovery_account'] == DEFAULT_WITNESS

    accounts_after = wallet.list_accounts()
    assert len(accounts_after) == len(account_before) + 1
    assert valid_name in accounts_after

    account_by_active_key = wallet.get_account_by_key(test_account_active_pub_key)[0][0]
    assert account_by_active_key == valid_name

    account_by_posting_key = wallet.get_account_by_key(test_accout_posting_pub_key)[0][0]
    assert account_by_posting_key == valid_name

    account_by_owner_key = wallet.get_account_by_key(test_account_owner_pub_key)[0][0]
    assert account_by_owner_key == valid_name

    account_by_memo_key = wallet.get_account_by_key(test_account_memo_key)[0]
    assert account_by_memo_key == []

    new_account_sp_balance_amount = str(wallet.get_account_sp_balance(valid_name)).split()[0]
    fee_amount = str(fee).split()[0]
    assert new_account_sp_balance_amount == fee_amount

    keys_auths = wallet.get_account_keys_auths(valid_name)
    assert keys_auths['owner'] == test_account_owner_pub_key
    assert keys_auths['active'] == test_account_active_pub_key
    assert keys_auths['posting'] == test_accout_posting_pub_key
    assert keys_auths['memo'] == test_account_memo_key


@pytest.mark.parametrize('name_and_error', [('', Errors.assert_exception),
                                            ('\'', Errors.assert_exception),
                                            ('ab', Errors.assert_exception),
                                            ('aB1', Errors.assert_exception),
                                            ('a_b', Errors.assert_exception),
                                            ('1ab', Errors.assert_exception),
                                            ('alalalalalalalala', Errors.tx_missing_active_auth),
                                            ('alice', Errors.uniqueness_constraint_violated)])
def test_create_account_with_invalid_name(wallet: Wallet, name_and_error):
    invalid_name, error = name_and_error
    response = wallet.create_account(DEFAULT_WITNESS, invalid_name, test_account_owner_pub_key)
    print(response)
    assert error.value == response['error']['data']['code']


@pytest.mark.parametrize('valid_name', ['joe', 'aaaaaaaaaaaaaaa1'])
def test_create_account_by_committee(wallet: Wallet, genesis: Genesis, valid_name):
    accounts_before = wallet.list_accounts()
    creator_balance_before = wallet.get_account_scr_balance(DEFAULT_WITNESS)
    print(wallet.create_account_by_committee(DEFAULT_WITNESS,
                                             newname=valid_name,
                                             owner=test_account_owner_pub_key,
                                             active=test_account_active_pub_key,
                                             posting=test_accout_posting_pub_key,
                                             memo=test_account_memo_key,))
    assert creator_balance_before == wallet.get_account_scr_balance(DEFAULT_WITNESS)

    assert wallet.get_account(valid_name)['recovery_account'] == DEFAULT_WITNESS

    accounts_after = wallet.list_accounts()
    assert len(accounts_after) == len(accounts_before) + 1
    assert valid_name in accounts_after

    account_by_active_key = wallet.get_account_by_key(test_account_active_pub_key)[0][0]
    assert account_by_active_key == valid_name

    account_by_posting_key = wallet.get_account_by_key(test_accout_posting_pub_key)[0][0]
    assert account_by_posting_key == valid_name

    account_by_owner_key = wallet.get_account_by_key(test_account_owner_pub_key)[0][0]
    assert account_by_owner_key == valid_name

    account_by_memo_key = wallet.get_account_by_key(test_account_memo_key)[0]
    assert account_by_memo_key == []

    new_account_sp_balance_amount = str(wallet.get_account_sp_balance(valid_name)).split()[0]
    registration_bonus_amount = genesis['registration_bonus'].split()[0]
    assert new_account_sp_balance_amount == registration_bonus_amount

    # TODO add assert to check registration_supply delta

    keys_auths = wallet.get_account_keys_auths(valid_name)
    assert keys_auths['owner'] == test_account_owner_pub_key
    assert keys_auths['active'] == test_account_active_pub_key
    assert keys_auths['posting'] == test_accout_posting_pub_key
    assert keys_auths['memo'] == test_account_memo_key


def test_registration_schedule(wallet: Wallet, genesis: Genesis):
    def expected_reward_value(schedule):
        registration_bonus = Amount(genesis['registration_bonus'])
        total_accounts = len(wallet.list_accounts())

        for s in schedule:
            if total_accounts <= s['users']:
                return registration_bonus*s['bonus_percent']//100
        return registration_bonus*schedule[-1]['bonus_percent']//100

    registration_schedule = list(genesis['registration_schedule'])
    total_users_in_schedule = 0
    for stage in registration_schedule:
        total_users_in_schedule += stage['users']
        stage['users'] = total_users_in_schedule

    names = ['martin', 'doug', 'kevin', 'joe', 'jim']
    accounts = [Account(name) for name in names]

    for account in accounts:
        wallet.create_account_by_committee(DEFAULT_WITNESS,
                                           account.name,
                                           active=account.active.get_public_key(),
                                           owner=account.owner.get_public_key(),
                                           posting=account.posting.get_public_key())

        assert wallet.get_account_sp_balance(account.name) == expected_reward_value(registration_schedule), \
            '{} sp balance differs from expected'.format(account.name)


@pytest.mark.parametrize('name_and_error', [('', Errors.assert_exception),
                                            ('\'', Errors.assert_exception),
                                            ('ab', Errors.assert_exception),
                                            ('aB1', Errors.assert_exception),
                                            ('a_b', Errors.assert_exception),
                                            ('1ab', Errors.assert_exception),
                                            ('alalalalalalalala', Errors.tx_missing_active_auth),
                                            ('alice', Errors.uniqueness_constraint_violated)])
def test_create_account_with_invalid_name_by_committee(wallet: Wallet, name_and_error):
    invalid_name, error = name_and_error
    response = wallet.create_account_by_committee(DEFAULT_WITNESS, invalid_name, test_account_owner_pub_key)
    print(response)
    assert error.value == response['error']['data']['code']


def test_create_budget(wallet: Wallet):
    wallet.create_budget(DEFAULT_WITNESS, Amount("10.000000000 SCR"), fmt_time_from_now(30))
    budget = wallet.get_budgets(DEFAULT_WITNESS)[0]

    per_block_for_10_blocks_budget = Amount('1.000000000 SCR')
    per_block_for_9_blocks_budget = Amount('1.034482758 SCR')

    assert DEFAULT_WITNESS in wallet.list_buddget_owners()
    assert Amount(budget['per_block']) in (per_block_for_10_blocks_budget, per_block_for_9_blocks_budget)
    assert budget['owner'] == DEFAULT_WITNESS


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

        activity_content_reward = full_content_reward*95/100
        assert witness_reward == full_content_reward - activity_content_reward, 'witness reward per block != expected'
        return full_content_reward

    def calculate_rewards_from_genesis():
        blocks_per_month = 864000
        days_in_month = 30
        days_in_2_years = 730
        rewards_supply = Amount(genesis['rewards_supply'])
        rewards_per_block = rewards_supply*days_in_month/days_in_2_years/blocks_per_month
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
    wallet.create_budget(DEFAULT_WITNESS, Amount("10000.000000000 SCR"), fmt_time_from_now(30))

    content_reward_after_budget_open = get_reward_per_block()
    assert content_reward_after_budget_open > content_reward_after_balancer_decrease, \
        'content reward not increased after budget open'


def test_post_comment(wallet: Wallet):
    post_kwargs = {'author': 'initdelegate',
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

    def validate_cashout_interval(comment: dict):
        time_format = '%Y-%m-%dT%H:%M:%S'
        date_start = datetime.datetime.strptime(comment['created'], time_format)
        date_finish = datetime.datetime.strptime(comment['cashout_time'], time_format)
        delta = date_finish - date_start
        assert delta.total_seconds()/3600/24 == 7.0

    def validate_url(comment: dict):
        if comment['parent_author']:
            assert comment['url'] == '/{category}/@{root_author}/{root_permlink}#@{author}/{permlink}'\
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


MIN_BLOCKS_TO_SAVE_INDEX = 21


def test_replay_blockchain(config, genesis, docker):
    """
    Test replay state of Node.

    :param Config config: Base config to run witness node
    :param Genesis genesis: Base genesis structure (users, accounts)
    :param DockerController docker: Pre-initialized image to run node
    """

    blocks_num = 5
    node = Node(config=config, genesis=genesis)
    node.generate_configs()
    # Start node, generate initial blocks in chain
    last_block = generate_blocks(
        node, docker, blocks_num + MIN_BLOCKS_TO_SAVE_INDEX
    )  # node was stopped
    assert last_block > 0, "Was not generated any block."

    node.drop_database()
    node.config['replay-blockchain'] = 'true'
    node.generate_configs()
    # Start node again, get header block
    last_block = generate_blocks(node, docker)  # node was stopped
    assert last_block >= blocks_num, \
        "Was generated %s blocks, should be >= %s" % (last_block, blocks_num)
    check_logs_on_errors(node.logs)


def test_restart_node(config, genesis, docker):
    """
    Test restart of the node.

    :param Config config: Base config to run witness node
    :param Genesis genesis: Base genesis structure (users, accounts)
    :param DockerController docker: Pre-initialized image to run node
    """

    blocks_num = 5
    node = Node(config=config, genesis=genesis)
    node.generate_configs()
    # Start node, generate initial blocks in chain
    last_block = generate_blocks(
        node, docker, blocks_num + MIN_BLOCKS_TO_SAVE_INDEX
    )  # node was stopped
    assert last_block > 0, "Was not generated any block."
    # Start node again, get header block
    last_block = generate_blocks(node, docker)  # node was stopped
    assert last_block >= blocks_num, \
        "Was generated %s blocks, should be >= %s" % (last_block, blocks_num)
    check_logs_on_errors(node.logs)


def test_node_monitoring_api_crash(wallet: Wallet, node: Node):
    result = wallet.get_last_block_duration_in_microseconds()
    assert type(result) is int
    node.read_logs()
    check_logs_on_errors(node.logs)