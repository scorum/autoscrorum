from os.path import join, isfile

import pytest

from src.config import Config
from src.docker_controller import DEFAULT_IMAGE_NAME
from src.docker_controller import DockerController
from src.genesis import Genesis
from src.node import Node
from src.node import TEST_TEMP_DIR
from src.utils import which, remove_dir_tree, create_dir
from src.wallet import Wallet
from tests.common import check_file_creation, DEFAULT_WITNESS

SCORUMD_BIN_PATH = which('scorumd')


def pytest_addoption(parser):
    parser.addoption('--target', action='store', default=SCORUMD_BIN_PATH, help='specify path to scorumd')
    parser.addoption('--image', action='store', default=DEFAULT_IMAGE_NAME, help='specify image for tests run')
    parser.addoption('--use-local-image', action='store_false', help='dont rebuild image')
    parser.addoption(
        '--long-term', action='store_true',
        help='Include long-term tests. Could take significantly long time.'
    )


@pytest.fixture(autouse=True)
def skip_long_term(request):
    if request.node.get_marker("skip_long_term"):
        if not request.config.getoption("--long-term"):
            pytest.skip("Long term tests are skipped. Use '--long-term' to enable it.")


@pytest.fixture(scope='session')
def rebuild_image(request):
    return request.config.getoption('--use-local-image')


@pytest.fixture(scope='session')
def bin_path(request, image):
    if image is not DEFAULT_IMAGE_NAME:
        return

    target = request.config.getoption('--target')
    if not target:
        pytest.fail('scorumd is not installed, specify path with --target={path}')

    possible_locations = [target,
                          join(target, 'scorumd'),
                          join(target, 'programs/scorumd/scorumd')]

    for location in possible_locations:
        if isfile(location):
            return location

    pytest.fail('scorumd not found, checked locations:\n'+' \n'.join(possible_locations))


@pytest.fixture(scope='session')
def image(request):
    return request.config.getoption('--image')


@pytest.fixture(scope='session', autouse=True)
def temp_dir():
    create_dir(TEST_TEMP_DIR)


@pytest.fixture(scope='function')
def genesis(request):

    accounts = {
        (DEFAULT_WITNESS, "80.000000000 SCR"),
        ('alice', "10.000000000 SCR"),
        ('bob', "10.000000000 SCR")
    }.union(
        ("test.test{}".format(i + 1), "10.000000000 SCR") for i in range(20)
    )

    g = Genesis()

    for name, amount in accounts:
        g.add_account(name, amount)

    g.add_witness_acc(DEFAULT_WITNESS)

    g.add_founder_acc('alice', 70.1)
    g.add_founder_acc('bob', 29.9)

    g.add_steemit_bounty_acc(DEFAULT_WITNESS)
    g.add_steemit_bounty_acc('bob')

    g.add_reg_committee_acc(DEFAULT_WITNESS)
    g.add_dev_committee_acc(DEFAULT_WITNESS)

    if hasattr(request, 'param'):
        for key, value in request.param.items():
            g[key] = value

    g.calculate_supplies()

    return g


@pytest.fixture(scope='session')
def default_config(docker):
    n = Node()  # node without pre-generated config file
    with docker.run_node(n):  # generate by binary default config
        check_file_creation(n.config_path)

    cfg = Config()
    cfg.read(n.config_path)
    yield cfg
    remove_dir_tree(n.work_dir)


@pytest.fixture(scope='function')
def config(default_config, genesis):
    witness = genesis.get_account(DEFAULT_WITNESS)
    default_config['rpc-endpoint'] = '0.0.0.0:8090'
    default_config['genesis-json'] = 'genesis.json'
    default_config['enable-stale-production'] = 'true'
    default_config['witness'] = '"{acc_name}"'.format(acc_name=witness.name)
    default_config['private-key'] = witness.get_signing_private()
    default_config['public-api'] += ' tags_api debug_node_api devcommittee_history_api'
    default_config["enable-plugin"] += ' witness tags debug_node'
    default_config.pop('history-blacklist-ops', no_exception=True)
    return default_config


@pytest.fixture(scope='function')
def node(config, genesis, docker):

    n = Node(config=config, genesis=genesis, logging=False)
    n.generate_configs()
    with docker.run_node(n):
        yield n

    if n.logging:
        n.read_logs()
        print(n.logs)

    remove_dir_tree(n.work_dir)


@pytest.fixture(scope='session')
def docker(image, bin_path, rebuild_image):
    d = DockerController(target_bin=bin_path)
    if rebuild_image:
        d.remove_image(image)
    d.set_image(image)
    yield d


@pytest.fixture(scope='function')
def wallet(node):
    with Wallet(node.get_chain_id(), node.rpc_endpoint, node.genesis.get_accounts()) as w:
        w.login("", "")
        w.get_api_by_name('database_api')
        w.get_api_by_name('network_broadcast_api')
        w.get_block(1, wait_for_block=True)
        yield w


"""
############################################# Static Test Data ########################################################
"""


@pytest.fixture(scope="session")
def alice_post():
    return {
        'author': 'alice',
        'permlink': 'alice-post',
        'parent_author': '',
        'parent_permlink': 'football',
        'title': 'alice football title',
        'body': 'alice football body',
        'json_metadata': '{"tags":["football", "sport", "test"]}'
    }


@pytest.fixture(scope="session")
def bob_post():
    return {
        'author': 'bob',
        'permlink': 'bob-post',
        'parent_author': '',
        'parent_permlink': 'hockey',
        'title': 'bob hockey title',
        'body': 'bob hockey body',
        'json_metadata': '{"tags":["hockey", "sport", "test"]}'
    }


@pytest.fixture(scope="session")
def initdelegate_post():
    return {
        'author': DEFAULT_WITNESS,
        'permlink': 'initdelegate-post',
        'parent_author': '',
        'parent_permlink': 'football',
        'title': 'initdelegate post title',
        'body': 'initdelegate post body',
        'json_metadata': '{"tags":["first_tag", "football", "sport", "initdelegate_posts", "test"]}'
    }


@pytest.fixture(params=['alice_post', 'bob_post', 'initdelegate_post'])
def post(request):
    return request.getfuncargvalue(request.param)


@pytest.fixture(params=['alice_post', 'bob_post'])
def not_witness_post(request):
    return request.getfuncargvalue(request.param)


@pytest.fixture(scope="session")
def only_posts(alice_post, bob_post, initdelegate_post):
    return [alice_post, bob_post, initdelegate_post]


@pytest.fixture(scope="session")
def bob_comment_lv1(initdelegate_post):
    return {
        'author': 'bob',
        'permlink': 'bob-comment-1',
        'parent_author': initdelegate_post["author"],
        'parent_permlink': initdelegate_post["permlink"],
        'title': 'bob comment title',
        'body': 'bob comment body',
        'json_metadata': '{"tags":["comment", "initdelegate_posts", "bob_tag"]}'
    }


@pytest.fixture(scope="session")
def alice_comment_lv1(initdelegate_post):
    return {
        'author': 'alice',
        'permlink': 'alice-comment-1',
        'parent_author': initdelegate_post["author"],
        'parent_permlink': initdelegate_post["permlink"],
        'title': 'alice comment title',
        'body': 'alice comment body',
        'json_metadata': '{"tags":["comment", "initdelegate_posts", "alice_tag"]}'
    }


@pytest.fixture(scope="session")
def post_with_comments(initdelegate_post, bob_comment_lv1, alice_comment_lv1):
    return [initdelegate_post, bob_comment_lv1, alice_comment_lv1]


@pytest.fixture(scope="session")
def alice_comment_lv2(bob_comment_lv1):
    return {
        'author': 'alice',
        'permlink': 'alice-comment-2',
        'parent_author': bob_comment_lv1["author"],
        'parent_permlink': bob_comment_lv1["permlink"],
        'title': 'alice comment_2 title',
        'body': 'alice comment_2 body',
        'json_metadata': '{"tags":["comment", "initdelegate_posts", "alice_tag"]}'
    }


@pytest.fixture(scope="session")
def post_with_multilvl_comments(initdelegate_post, bob_comment_lv1, alice_comment_lv2):
    return [initdelegate_post, bob_comment_lv1, alice_comment_lv2]


@pytest.fixture(params=['only_posts', 'post_with_comments', 'post_with_multilvl_comments'])
def posts(request):
    return request.getfuncargvalue(request.param)
