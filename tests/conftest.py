import os
import shutil
import pytest

from autoscorum.genesis import Genesis
from autoscorum.node import Node
from autoscorum.node import DockerController
from autoscorum.rpc_client import RpcClient

DEFAULT_IMAGE_NAME = 'autonode'
TEST_TEMP_DIR = '/tmp/autoscorum'

acc_name = "initdelegate"
acc_public_key = "SCR7R1p6GyZ3QjW3LrDayEy9jxbbBtPo9SDajH5QspVdweADi7bBi"
acc_private_key = "5K8ZJUYs9SP47JgzUY97ogDw1da37yuLrSF5syj2Wr4GEvPWok6"


def pytest_addoption(parser):
    parser.addoption('--image', metavar='image', default=DEFAULT_IMAGE_NAME, help='specify image for tests run')


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


@pytest.fixture()
def genesis():
    g = Genesis()
    g["init_rewards_supply"] = "1000000.000000000 SCR"
    g["init_accounts_supply"] = "210000.000000000 SCR"
    g.add_account(acc_name=acc_name,
                  public_key=acc_public_key,
                  scr_amount="110000.000000000 SCR",
                  witness=True)

    g.add_account(acc_name='alice',
                  public_key="SCR8TBVkvbJ79L1A4e851LETG8jurXFPzHPz87obyQQFESxy8pmdx",
                  scr_amount="100000.000000000 SCR")
    return g


@pytest.fixture()
def node(genesis):
    n = Node(genesis=genesis)
    n.config['witness'] = '"{acc_name}"'.format(acc_name=acc_name)
    n.config['private-key'] = acc_private_key
    n.config['public-api'] = "database_api login_api account_by_key_api"
    n.config['enable-plugin'] = 'witness account_history account_by_key'

    return n


@pytest.fixture(scope='module')
def docker(image):
    d = DockerController(image)
    yield d
    d.stop_all()


@pytest.fixture()
def rpc(node, docker):
    docker.run_node(node)
    client = RpcClient(node, [acc_private_key])
    client.open_ws()
    client.login("", "")
    client.get_api_by_name('database_api')
    client.get_api_by_name('network_broadcast_api')
    client.get_block(1, wait_for_block=True)
    yield client
    client.close_ws()
