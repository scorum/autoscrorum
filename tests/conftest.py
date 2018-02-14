import os
import shutil
import pytest

DEFAULT_IMAGE_NAME = 'autonode'
TEST_TEMP_DIR = '/tmp/autoscorum'


def pytest_addoption(parser):
    parser.addoption('--image', metavar='image', default=DEFAULT_IMAGE_NAME, help='specify image for tests run')


@pytest.fixture(scope='session')
def image(request):
    return request.config.getoption('--image')


@pytest.fixture(scope='module', autouse=True)
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
