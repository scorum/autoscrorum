from setuptools import setup
from setuptools import find_packages

setup(
    name='autoscorum',
    version='0.0.1',
    packages=['autoscorum'],
    install_requires=['docker',
                      'steem',
                      'pytest',
                      'websocket-client',
                      'pytest-timeout',
                      'secp256k1']
)
