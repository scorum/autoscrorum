import os
import shutil
import pytest
import time

from autoscorum.genesis import Genesis
from autoscorum.node import Node
from autoscorum.docker_controller import DockerController
from autoscorum.wallet import Wallet
from autoscorum.utils import which
from autoscorum.config import Config

from autoscorum.node import TEST_TEMP_DIR
from autoscorum.docker_controller import DEFAULT_IMAGE_NAME

SCORUMD_BIN_PATH = which('scorumd')

DEFAULT_WITNESS = "initdelegate"


def pytest_addoption(parser):
    parser.addoption('--target', action='store', default=SCORUMD_BIN_PATH, help='specify path to scorumd')
    parser.addoption('--image', action='store', default=DEFAULT_IMAGE_NAME, help='specify image for tests run')
    parser.addoption('--use-local-image', action='store_false', help='dont rebuild image')


@pytest.fixture(scope='session')
def rebuild_image(request):
    return request.config.getoption('--use-local-image')


@pytest.fixture(scope='session')
def bin_path(request, image):
    if image is DEFAULT_IMAGE_NAME:
        target = request.config.getoption('--target')
        if not target:
            pytest.fail('scorumd is not installed, specify path with --target={path}')

        possible_locations = [target,
                              os.path.join(target, 'scorumd'),
                              os.path.join(target, 'programs/scorumd/scorumd')]

        for location in possible_locations:
            if os.path.isfile(location):
                return location

        fail_message = 'scorumd not found, checked locations:\n'+' \n'.join(possible_locations)

        pytest.fail(fail_message)
    return None


@pytest.fixture(scope='session')
def image(request):
    return request.config.getoption('--image')


@pytest.fixture(scope='function', autouse=True)
def temp_dir():
    try:
        os.mkdir(TEST_TEMP_DIR)
    except FileExistsError:
        shutil.rmtree(TEST_TEMP_DIR)
        os.mkdir(TEST_TEMP_DIR)

    yield

    try:
        shutil.rmtree(TEST_TEMP_DIR)
    except FileNotFoundError:
        pass


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

    g.calculate_supplies()

    if hasattr(request, 'param'):
        for key, value in request.param.items():
            g[key] = value
    return g


@pytest.fixture(scope='function')
def default_config(docker):
    n = Node()  # node without pre-generated config file
    with docker.run_node(n):  # generate by binary default config
        for i in range(50):
            if os.path.exists(n.config_path):
                break
            time.sleep(0.1)
        assert os.path.exists(n.config_path), \
            "Config file wasn't created after 5 seconds."

    cfg = Config()
    cfg.read(n.config_path)
    return cfg


@pytest.fixture(scope='function')
def config(default_config, genesis):
    witness = genesis.get_account(DEFAULT_WITNESS)
    default_config['rpc-endpoint'] = '0.0.0.0:8090'
    default_config['genesis-json'] = 'genesis.json'
    default_config['enable-stale-production'] = 'true'
    default_config['witness'] = '"{acc_name}"'.format(acc_name=witness.name)
    default_config['private-key'] = witness.get_signing_private()
    default_config['public-api'] = default_config['public-api'].replace('\n', " tags_api\n")
    default_config["enable-plugin"] = 'witness tags ' + default_config["enable-plugin"]
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
