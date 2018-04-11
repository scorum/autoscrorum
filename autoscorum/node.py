import tempfile
import os

from pathlib import Path
from hashlib import sha256

from .config import Config
from . import utils


TEST_TEMP_DIR = '/tmp/autoscorum'
SCORUM_BIN = 'scorumd'


chain_params = {"chain_id": None,
                "prefix": "SCR",
                "scorum_symbol": "SCR",
                "sp_symbol": "SP",
                "scorum_prec": 9,
                "sp_prec": 9}


class Node(object):
    def __init__(self, config=Config(), genesis=None, logging=True):
        self.config = config
        self._genesis = genesis
        self.logging = logging
        self.logs = ""
        self.rpc_endpoint = None
        self._dir_name = None

    def get_chain_id(self):
        if not chain_params["chain_id"]:
            for line in self.logs:
                if "node chain ID:" in line:
                    chain_params["chain_id"] = line.split(" ")[-1]
        return chain_params["chain_id"]

    def read_logs(self):
        log_file = os.path.join(self._dir_name, 'logs/current')
        with open(log_file, 'r') as logs:
            for line in logs:
                self.logs += line

    def setup(self):
        self._dir_name = tempfile.mkdtemp(self.config['witness'][1:-1], dir=TEST_TEMP_DIR)

        genesis_path = os.path.join(self._dir_name, 'genesis.json')
        config_path = os.path.join(self._dir_name, 'config.ini')

        if not os.path.exists(os.path.dirname(genesis_path)):
            os.makedirs(os.path.dirname(genesis_path))

        with open(genesis_path, 'w') as genesis:
            g = self._genesis.dump()
            genesis.write(g)
            chain_params["chain_id"] = sha256(g.encode()).hexdigest()
        with open(config_path, 'w') as config:
            config.write(self.config.dump())

        return os.path.dirname(genesis_path)
