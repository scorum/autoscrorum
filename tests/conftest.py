import os
import shutil
import pytest

from autoscorum.genesis import Genesis
from autoscorum.node import Node
from autoscorum.docker_controller import DockerController
from autoscorum.wallet import Wallet
from autoscorum.account import Account
from autoscorum.utils import which

from autoscorum.node import TEST_TEMP_DIR
from autoscorum.docker_controller import DEFAULT_IMAGE_NAME

initdelegate = Account('initdelegate')

SCORUMD_BIN_PATH = which('scorumd')


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
    g = Genesis()
    g.add_account(acc_name=initdelegate.name,
                  public_key=initdelegate.get_active_public(),
                  scr_amount="80.000000000 SCR",
                  witness=True)
    g.add_account(acc_name='alice',
                  public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                  scr_amount="10.000000000 SCR")
    g.add_account(acc_name='bob',
                  public_key="SCR7w8tySAVQmJ95xSL8SS2GJJCws9s2gCY85DSAEALMFPmaMKA6p",
                  scr_amount="10.000000000 SCR")

    g["founders"] = [{"name": "alice",
                      "sp_percent": 70.1},
                     {"name": "bob",
                      "sp_percent": 29.9}]
    g["steemit_bounty_accounts"] = [{"name": "initdelegate",
                                     "sp_amount": "50.000000000 SP"},
                                    {"name": "bob",
                                     "sp_amount": "50.000000000 SP"}]
    g['development_committee'] = [initdelegate.name]
    if hasattr(request, 'param'):
        for key, value in request.param.items():
            g[key] = value
    return g


@pytest.fixture(scope='function')
def node(genesis, docker):
    n = Node(genesis=genesis, logging=False)
    n.config['witness'] = '"{acc_name}"'.format(acc_name=initdelegate.name)
    n.config['private-key'] = initdelegate.get_active_private()
    n.config['public-api'] = "database_api login_api account_by_key_api"
    n.config['enable-plugin'] = 'witness blockchain_history account_by_key'

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
    with Wallet(node, [initdelegate]) as w:
        w.login("", "")
        w.get_api_by_name('database_api')
        w.get_api_by_name('network_broadcast_api')
        w.get_block(1, wait_for_block=True)
        yield w
