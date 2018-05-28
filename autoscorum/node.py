import tempfile
import os

from hashlib import sha256
from .config import Config


TEST_TEMP_DIR = '/tmp/autoscorum'
SCORUM_BIN = 'scorumd'


class Node(object):
    def __init__(self, config=None, genesis=None, logging=True):
        self.config = config
        self.genesis = genesis
        self.logging = logging
        self.logs = ""
        self.rpc_endpoint = None
        self.chain_params = None
        self.work_dir = None
        self.genesis_path = None
        self.config_path = None
        self._setup()

    def get_chain_id(self):
        if not self.chain_params["chain_id"]:
            for line in self.logs:
                if "node chain ID:" in line:
                    self.chain_params["chain_id"] = line.split(" ")[-1]
        return self.chain_params["chain_id"]

    def read_logs(self):
        log_file = os.path.join(self.work_dir, 'logs/current')
        with open(log_file, 'r') as logs:
            for line in logs:
                self.logs += line

    def _setup(self):
        self.chain_params = {
            "chain_id": None, "prefix": "SCR", "scorum_symbol": "SCR",
            "sp_symbol": "SP", "scorum_prec": 9, "sp_prec": 9
        }

        if self.config is None:
            self.config = Config()
            self.config['witness'] = '"dummy"'

        self.work_dir = tempfile.mkdtemp(
            prefix=self.config['witness'][1:-1], dir=TEST_TEMP_DIR
        )

        self.genesis_path = os.path.join(self.work_dir, 'genesis.json')
        self.config_path = os.path.join(self.work_dir, 'config.ini')

    def generate_configs(self):
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)

        if self.genesis is not None:
            with open(self.genesis_path, 'w') as gfd:  # genesis file descriptor
                g = self.genesis.dump()
                self.chain_params["chain_id"] = sha256(g.encode()).hexdigest()
                gfd.write(g)

        if self.config is not None:
            with open(self.config_path, 'w') as cfd:  # config file descriptor
                cfd.write(self.config.dump())
