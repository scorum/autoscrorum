import os
import re
import time
from functools import partial
from multiprocessing import Pool

from delayed_assert import expect, assert_expectations

from src.wallet import Wallet

DEFAULT_WITNESS = "initdelegate"


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


def parallel_create_posts(posts, node):
    p = Pool(processes=len(posts))
    return p.map(partial(post_comment, node=node), posts)


def validate_response(response, op: str, required_params=None):

    assert "error" not in response, "%s operation failed: %s" % (op, response["error"])

    if not required_params:
        required_params = []

    for param in required_params:
        try:
            key, value = param
        except ValueError:
            key = param
            value = str  # default type for most fields
        val_type = type(value)
        if val_type == type:  # e.g. if was passed type, not value
            val_type = value
        expect(key in response, "Parameter '%s' is missing in response: %s" % (key, response))
        if key in response:
            expect(
                isinstance(response[key], val_type),
                "Parameter '%s' has invalid value type '%s', expected '%s': %s" %
                (key, type(response[key]), val_type, response)
            )
            if val_type != value and isinstance(response[key], val_type):
                expect(
                    response[key] == value,
                    "Parameter '%s' has invalid value '%s', expected '%s': %s" %
                    (key, response[key], value, response)
                )
    assert_expectations()


def validate_error_response(response, op: str, error_message="Assert Exception"):
    assert "error" in response and error_message in response["error"]["message"], \
        "%s operation should fail but passed with result: %s" % (op, response["error"])


def apply_hardfork(wallet: Wallet, hf_id: int):
    assert hf_id > 0
    for i in range(1, hf_id + 1):
        wallet.get_block(i + 1, wait_for_block=True)
        assert wallet.debug_has_hardfork(i - 1)
        wallet.debug_set_hardfork(i)
