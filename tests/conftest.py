from os.path import join, isfile

from scorum.utils.files import which, remove_dir_tree, create_dir

from automation.config import Config
from automation.docker_controller import DEFAULT_IMAGE_NAME, DockerController
from automation.genesis import Genesis
from automation.node import Node, TEST_TEMP_DIR
from automation.wallet import Wallet
from tests.common import check_file_creation
from tests.data import *

SCORUMD_BIN_PATH = which('scorumd')


def pytest_addoption(parser):
    parser.addoption('--target', action='store', default=SCORUMD_BIN_PATH, help='specify path to scorumd')
    parser.addoption('--image', action='store', default=DEFAULT_IMAGE_NAME, help='specify image for tests run')
    parser.addoption('--use-local-image', action='store_false', help='dont rebuild image')
    parser.addoption(
        '--long-term', action='store_true',
        help='Include long-term tests. Could take significantly long time.'
    )
    parser.addoption('--logging', action='store_true', default=False, help='print out node logs')


@pytest.fixture(autouse=True)
def skip_long_term(request):
    if request.node.get_marker("skip_long_term"):
        if not request.config.getoption("--long-term"):
            pytest.skip("Long term tests are skipped. Use '--long-term' to enable it.")


@pytest.fixture(scope='session')
def rebuild_image(request):
    return request.config.getoption('--use-local-image')


@pytest.fixture(scope='session')
def logging(request):
    return request.config.getoption('--logging')


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


@pytest.fixture(scope='session')
def genesis(request):

    accounts = {
        (DEFAULT_WITNESS, "80.000000000 SCR"),
        ('alice', "10.000000000 SCR"),
        ('bob', "10.000000000 SCR")
    }.union(
        ("test.test{}".format(i + 1), "20.000000000 SCR") for i in range(20)
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
    test_apis = [
        'database_api',
        'login_api',
        'network_broadcast_api',
        'account_by_key_api',
        'blockchain_history_api',
        'account_history_api',
        'account_statistics_api',
        'chain_api',
        'tags_api',
        'node_monitoring_api',
        'debug_node_api',
        'devcommittee_history_api',
        'advertising_api',
        'betting_api'
    ]

    test_plugins = [
        'witness',
        'blockchain_history',
        'account_by_key',
        'account_statistics',
        'tags',
        'blockchain_monitoring',
        'debug_node'
    ]

    witness = genesis.get_account(DEFAULT_WITNESS)
    default_config['rpc-endpoint'] = '0.0.0.0:8090'
    default_config['genesis-json'] = 'genesis.json'
    default_config['enable-stale-production'] = 'true'
    default_config['witness'] = '"{acc_name}"'.format(acc_name=witness.name)
    default_config['private-key'] = witness.get_signing_private()
    default_config['public-api'] = " ".join(test_apis)
    default_config["enable-plugin"] = " ".join(test_plugins)
    default_config.pop('history-blacklist-ops')
    default_config.pop('seed-node')
    return default_config


@pytest.fixture(scope='function')
def node(config, genesis, docker, logging):

    n = Node(config=config, genesis=genesis, logging=logging)
    n.generate_configs()
    with docker.run_node(n):
        yield n

    if logging:
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
