import os
import docker
import shutil
import tempfile
from docker.errors import ImageNotFound
from contextlib import contextmanager

from .node import Node
from . import utils

DEFAULT_IMAGE_NAME = 'autonode'
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

        self._image = image
        try:
            self.docker.images.get(image)
        except ImageNotFound:
            if image is DEFAULT_IMAGE_NAME:
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


def test_1():
    print('hello!')
    node = Node()
