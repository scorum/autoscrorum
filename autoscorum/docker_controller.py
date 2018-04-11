import os

import docker
import shutil
import tempfile
from docker.errors import ImageNotFound
from contextlib import contextmanager

from .node import Node
from .node import SCORUM_BIN

DEFAULT_IMAGE_NAME = 'autonode'
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
    def __init__(self, target_bin=None):
        self.docker = docker.from_env()
        self._image = None
        self._target_bin = target_bin

    def remove_image(self, image):
        try:
            self.docker.images.remove(image, force=True, noprune=False)
        except ImageNotFound:
            pass

    @contextmanager
    def run_node(self, node: Node, image: str=None):
        if image:
            self.set_image(image)
        volume_src = node.setup()

        container = self.docker.containers.run(self._image,
                                               detach=True,
                                               auto_remove=True,
                                               volumes={volume_src: {'bind': '/var/lib/scorumd', 'mode': 'rw'}})

        node.rpc_endpoint = "{ip}:{port}".format(ip=self.get_ip(container),
                                                 port=node.config['rpc-endpoint'].split(':')[1])

        yield container
        self.stop(container)

    def set_image(self, image: str):
        self._image = image
        try:
            self.docker.images.get(image)
        except ImageNotFound:
            if image is DEFAULT_IMAGE_NAME:
                self._create_default_image()
            else:
                self.docker.images.pull(image)

    def _create_default_image(self):
        with self._prepare_context() as context:
            self.docker.images.build(path=context, tag=self._image)

    @contextmanager
    def _prepare_context(self):
        with tempfile.TemporaryDirectory() as docker_context:
            shutil.copyfile(self._target_bin, os.path.join(docker_context, SCORUM_BIN))
            with open(os.path.join(docker_context, 'Dockerfile'), 'w') as file:
                file.write(DOCKERFILE)
            yield docker_context

    @staticmethod
    def inspect_container(container):
        low_api = docker.APIClient()
        return low_api.inspect_container(container.id)

    @staticmethod
    def stop(container):
        container.remove(force=True, v=False)

    @staticmethod
    def get_ip(container):
        info = DockerController.inspect_container(container)
        ip = info['NetworkSettings']['IPAddress']
        return ip
