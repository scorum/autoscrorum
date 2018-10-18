from hashlib import sha256
from os.path import join

from scorum.utils.files import create_temp_dir, remove_file

from src.config import Config

TEST_TEMP_DIR = '/tmp/autoscorum'
SCORUM_BIN = 'scorumd'


class Node(object):

    GENESIS_FILE = 'genesis.json'
    CONFIG_FILE = 'config.ini'
    NODE_LOG = 'node.log'
    SHARED_MEMORY_BIN = 'shared_memory.bin'
    SHARED_MEMORY_META = 'shared_memory.meta'
    BLOCK_LOG = 'block_log'
    BLOCK_LOG_INDEX = 'block_log.index'
    DATABASE_FILES = [
        SHARED_MEMORY_BIN, SHARED_MEMORY_META,
        BLOCK_LOG, BLOCK_LOG_INDEX
    ]

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
        self.logs_path = None
        self._setup()

    def get_chain_id(self):
        if not self.chain_params["chain_id"]:
            for line in self.logs:
                if "node chain ID:" in line:
                    self.chain_params["chain_id"] = line.split(" ")[-1]
        return self.chain_params["chain_id"]

    def read_logs(self):
        self.logs = ""  # empty logs param before repeat reading logs
        with open(self.logs_path, 'r') as f:
            for line in f:
                self.logs += line

    def drop_database(self, clean_logs=False, remove_index=False):
        for file in self.DATABASE_FILES:
            if (not clean_logs and file == self.BLOCK_LOG) \
                    or (not remove_index and file == self.BLOCK_LOG_INDEX):
                continue
            remove_file(join(self.work_dir, 'blockchain', file))

    def _setup(self):
        self.chain_params = {
            "chain_id": None, "prefix": "SCR", "scorum_symbol": "SCR",
            "sp_symbol": "SP", "scorum_prec": 9, "sp_prec": 9
        }

        if self.config is None:
            self.config = Config()
            self.config['witness'] = '"dummy"'

        self.work_dir = create_temp_dir(TEST_TEMP_DIR, self.config['witness'][1:-1])

        self.genesis_path = join(self.work_dir, self.GENESIS_FILE)
        self.config_path = join(self.work_dir, self.CONFIG_FILE)
        self.logs_path = join(self.work_dir, 'logs', self.NODE_LOG)

    def generate_configs(self):
        if self.genesis is not None:
            with open(self.genesis_path, 'w') as gfd:  # genesis file descriptor
                g = self.genesis.dump()
                self.chain_params["chain_id"] = sha256(g.encode()).hexdigest()
                gfd.write(g)

        if self.config is not None:
            with open(self.config_path, 'w') as cfd:  # config file descriptor
                cfd.write(self.config.dump())
