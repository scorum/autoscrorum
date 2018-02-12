import docker
import pytest
from autoscorum.node import Container


DEFAULT_IMAGE_NAME = 'autonode'

def pytest_addoption(parser):
    parser.addoption('--image', metavar='image', default=DEFAULT_IMAGE_NAME, help='specify image for tests run')


@pytest.fixture
def containeer(request):
    image_name = request.config.getoption('--image')
    containeer = Container(image_name)

