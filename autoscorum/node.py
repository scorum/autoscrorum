import shutil
import tempfile
import docker
import os

from docker.errors import ImageNotFound
from contextlib import contextmanager
from pathlib import Path
from hashlib import sha256

from autoscorum.config import Config
from autoscorum import utils


TEST_TEMP_DIR = '/tmp/autoscorum'
SCORUM_BIN = 'scorumd'

CONFIG_DIR = '/var/lib/scorumd'
DOCKERFILE = '''FROM phusion/baseimage:0.9.19
ADD ./scorumd /usr/local/bin


ENV HOME '{CONFIG_DIR}'
WORKDIR {CONFIG_DIR}
RUN useradd -s /bin/bash -m -d {CONFIG_DIR} scorumd
RUN chown scorumd:scorumd -R {CONFIG_DIR}
RUN chown scorumd:scorumd /usr/local/bin/scorumd
RUN chmod 0755 /usr/local/bin/scorumd

VOLUME ["{CONFIG_DIR}"]

EXPOSE 8090
EXPOSE 2001

USER scorumd
ENTRYPOINT ["/usr/local/bin/scorumd"]
CMD ["--config-file", "{CONFIG_DIR}/config.ini"]

'''.format(CONFIG_DIR=CONFIG_DIR)

chain_params = {"chain_id": None,
                "prefix": "SCR",
                "scorum_symbol": "SCR",
                "sp_symbol": "SP",
                "scorum_prec": 9,
                "sp_prec": 9}


class Node(object):
    docker = docker.from_env()

    def __init__(self, config=Config(), genesis=None, logging=True):
        self._bin_path = None
        self.config = config
        self._genesis = genesis
        self.logging = logging
        self.logs = ""
        self.rpc_endpoint = None

    @staticmethod
    def check_binaries():
        bin_path = Path(utils.which(SCORUM_BIN))
        assert bin_path.exists(), "scorumd does not exists"
        assert bin_path.is_file(), "scorumd is not a file"

    def get_chain_id(self):
        if not chain_params["chain_id"]:
            for line in self.logs:
                if "node chain ID:" in line:
                    chain_params["chain_id"] = line.split(" ")[-1]
        return chain_params["chain_id"]

    def setup(self):
        dir_name = os.path.basename(tempfile.mktemp(self.config['witness'][1:-1]))

        genesis_path = os.path.join(TEST_TEMP_DIR, dir_name, 'genesis.json')
        config_path = os.path.join(TEST_TEMP_DIR, dir_name, 'config.ini')

        if not os.path.exists(os.path.dirname(genesis_path)):
            os.makedirs(os.path.dirname(genesis_path))


        with open(genesis_path, 'w') as genesis:
            g = self._genesis.dump()
            genesis.write(g)
            chain_params["chain_id"] = sha256(g.encode()).hexdigest()
        with open(config_path, 'w') as config:
            config.write(self.config.dump())

        return os.path.dirname(genesis_path)


class DockerController:
    def __init__(self, image):
        self.docker = docker.from_env()
        self._image = None
        self._started_containers = []

        self.set_image(image)

    def run_node(self, node: Node):
        volume_src = node.setup()

        container = self.docker.containers.run(self._image,
                                               detach=True,
                                               auto_remove=True,
                                               volumes={volume_src: {'bind': '/var/lib/scorumd', 'mode': 'rw'}})
        self._started_containers.append(container)

        node.rpc_endpoint = "{ip}:{port}".format(ip=self.get_ip(container),
                                                 port=node.config['rpc-endpoint'].split(':')[1])
        return container

    def set_image(self, image: str):
        from tests.conftest import DEFAULT_IMAGE_NAME as DEFAULT
        self._image = image  
        try:
            self.docker.images.get(image)
        except ImageNotFound:
            if image is DEFAULT:
                Node.check_binaries()
                self._create_default_image()
            else:
                self.docker.images.pull(image)

    def _create_default_image(self):
        with self._prepare_context() as context:
            self.docker.images.build(path=context, tag=self._image)

    @contextmanager
    def _prepare_context(self):
        with tempfile.TemporaryDirectory() as docker_context:
            shutil.copyfile(utils.which(SCORUM_BIN), os.path.join(docker_context, SCORUM_BIN))
            with open(os.path.join(docker_context, 'Dockerfile'), 'w') as file:
                file.write(DOCKERFILE)
            yield docker_context

    @staticmethod
    def read_node_logs(container, node):
        for line in container.logs(stream=True):
            node.logs += line.decode("utf-8")

    @staticmethod
    def inspect_container(container):
        low_api = docker.APIClient()
        return low_api.inspect_container(container.id)

    def stop(self, container):
        container.stop()
        self._started_containers.remove(container)

    def stop_all(self):
        for cont in self._started_containers:
            self.stop(cont)

    @staticmethod
    def get_ip(container):
        info = DockerController.inspect_container(container)
        ip = info['NetworkSettings']['IPAddress']
        return ip
