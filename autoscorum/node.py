import shutil
import tempfile
import io
import tarfile
import docker
import os
import threading

from docker.errors import ImageNotFound
from contextlib import contextmanager
from contextlib import closing
from pathlib import Path
from hashlib import sha256

from autoscorum.config import Config
from autoscorum import utils

SCORUM_BIN = 'scorumd'

CONTAINER_DATADIR_PATH = '/usr/local/src/scorum/witness_node_data_dir'
CONTAINER_BIN_PATH = '/usr/local/src/scorum'
DOCKERFILE = f'''FROM phusion/baseimage:0.9.19
CMD ['/sbin/my_init']

RUN mkdir {CONTAINER_BIN_PATH}
RUN mkdir {CONTAINER_DATADIR_PATH}
ADD ./scorumd {CONTAINER_BIN_PATH}

WORKDIR {CONTAINER_BIN_PATH}
RUN chown -R root:root ./scorumd
RUN chmod 0755 ./scorumd

EXPOSE 8090
'''
DOCKER_IMAGE_NAME = 'autonode'


class Node(object):
    docker = docker.from_env()

    chain_params = {"chain_id": None,
                    "prefix": "SCR",
                    "scorum_symbol": "SCR",
                    "sp_symbol": "SP",
                    "scorum_prec": 3,
                    "sp_prec": 6}

    def __init__(self, config=Config(), genesis=None, logging=True):
        self._bin_path = None
        self.config = config
        self._container = None
        self._inspect_info = {}
        self._genesis = genesis
        self._logging = logging
        self.logs = ""
        self.addr = '127.0.0.1:8090'


        self._bin_path = Path(utils.which(SCORUM_BIN))

        assert self._bin_path.exists(), "scorumd does not exists"
        assert self._bin_path.is_file(), "scorumd is not a file"

    def _create_docker_image(self):
        with self._prepare_context() as context:
            self.docker.images.build(path=context, tag=DOCKER_IMAGE_NAME)

    @contextmanager
    def _prepare_context(self):
        with tempfile.TemporaryDirectory() as docker_context:
            shutil.copyfile(utils.which(SCORUM_BIN), os.path.join(docker_context, SCORUM_BIN))
            with open(os.path.join(docker_context, 'Dockerfile'), 'w') as file:
                file.write(DOCKERFILE)
            yield docker_context

    def run(self, command=None):
        return 0
        client = self.docker
        if not command:
            args = ['--enable-stale-production']
            if self._genesis:
                args.append('-g genesis.json')
                pass
            command = self.get_run_command(*args)

        try:
            client.images.get(DOCKER_IMAGE_NAME)
        except ImageNotFound:
            self._create_docker_image()
        self._run_container(command)

    def get_chain_id(self):
        return "f9ff83a1c168da969782cd54e3514f975e797bcd874a2f63323b3edebfbc367f"
        if not self.chain_params["chaind_id"]:
            for line in self.logs:
                if "node chain ID:" in line:
                    self.chain_params["chaind_id"] = line.split(" ")[-1]
        return self.chain_params["chaind_id"]

    def stop(self):
        return 0
        self._container.stop()

    def _read_logs(self):
        for line in self._container.logs(stream=True):
            self.logs += line.decode("utf-8")

    def _run_container(self, command):
        self._container = self.docker.containers.create(image=DOCKER_IMAGE_NAME,
                                                        command=command,
                                                        detach=True,
                                                        auto_remove=True)

        with utils.write_to_tempfile(self.config.dump()) as config:
            self.put_to_container(src=config, dst=os.path.join(CONTAINER_DATADIR_PATH, 'config.ini'))
        if self._genesis:
            g = self._genesis.dump()
            with utils.write_to_tempfile(g) as genesis:
                self.put_to_container(src=genesis, dst=os.path.join(CONTAINER_BIN_PATH, 'genesis.json'))
            self.chain_params["chaind_id"] = sha256(g.encode()).hexdigest()

        self._container.start()
        if self._logging:
            logs_thread = threading.Thread(target=self._read_logs)
            logs_thread.daemon = True
            logs_thread.start()
        self._inspect_container()

    def _inspect_container(self):
        low_api = docker.APIClient()
        inspect_info = low_api.inspect_container(self._container.id)
        self._inspect_info = inspect_info
        ip = inspect_info['NetworkSettings']['IPAddress']
        port = inspect_info['NetworkSettings']['Ports']
        port = list(port.keys())[0].split("/", 1)[0]
        self.addr = f'{ip}:{port}'

    def put_to_container(self, src, dst):
        with closing(io.BytesIO()) as tarstream:
            with closing(tarfile.TarFile(fileobj=tarstream, mode='w')) as tar:
                tar.add(src, arcname=os.path.basename(dst))

            tarstream.seek(0)
            self._container.put_archive(os.path.dirname(dst), tarstream)

    @staticmethod
    def get_run_command(*args):
        command = f'./{SCORUM_BIN} ' + ' '.join(args)
        return command
