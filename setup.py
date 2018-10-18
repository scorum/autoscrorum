from setuptools import setup, find_packages

required = [
    "delayed_assert",
    "docker",
    "pylama",
    "pytest",
    "pytest-pep8",
    "pytest-timeout",
    "pytest-xdist",
    "pytz",
    "requests",
    "scorum",
    "secp256k1",
    "sortedcontainers",
    "websocket-client",
]

setup(
    name='scorum',
    version='0.3.0',
    packages=find_packages(exclude=["tests"]),
    long_description=open('README.md').read(),
    install_requires=required
)
