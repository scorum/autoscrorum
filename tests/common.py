import re
import os
import time

from src.wallet import Wallet


def check_logs_on_errors(logs):
    """
    Check given string on existence of common 'error keywords'.

    :param str logs:
    """
    re_errors = r"(warning|error|critical|exception|traceback)"
    m = re.match(re_errors, logs, re.IGNORECASE)
    assert m is None, "In logs presents error message: %s" % m.group()


def check_file_creation(filepath, sec=5):
    """
    Check if file on given path was created in specified time.

    :param str filepath: Path to file.
    :param int sec: Maximum number of seconds to wait.
    """
    for i in range(sec * 10):
        if os.path.exists(filepath):
            break
        time.sleep(0.1)
    assert os.path.exists(filepath), \
        "File wasn't created after %d seconds. Path %s" % (sec, filepath)


def generate_blocks(node, docker, num=1):
    """
    Run node, wait until N blocks will be generated, stop node.

    :param Node node: Node to run
    :param DockerController docker: Docker to run container
    :param int num: Number of blocks to generate
    :return int: Number of head block
    """
    with docker.run_node(node):
        with Wallet(
                node.get_chain_id(), node.rpc_endpoint,
                node.genesis.get_accounts()
        ) as w:
            w.get_block(
                num, wait_for_block=True,
                time_to_wait=3 * num  # 3 sec on each block
            )
            return w.get_dynamic_global_properties()['head_block_number']


def post_comment(post_kwargs, node):
    with Wallet(node.get_chain_id(), node.rpc_endpoint, node.genesis.get_accounts()) as w:
        w.login("", "")
        w.get_api_by_name('database_api')
        w.get_api_by_name('network_broadcast_api')
        return w.post_comment(**post_kwargs)
