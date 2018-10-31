import os
import re
import time
import uuid
from functools import partial
from multiprocessing import Pool

from delayed_assert import expect, assert_expectations
from automation.wallet import Wallet

DEFAULT_WITNESS = "initdelegate"

# Error regexps
RE_ERROR_KWDS = r".{50}(warning|error|critical|exception|traceback).{50}"
RE_IDX_OUT_OF_RANGE = r"Can\'t get object of type .* It\'s not in index."
RE_OBJECT_NOT_EXIST = r"Assert Exception\n.* with (uu)?id .* doesn\'t exist"
RE_OBJECT_EXIST = r"Assert Exception\n.* with (uu)?id .* already exist"
RE_OP_IS_LOCKED = r"Assert Exception\n.* Operation .* is locked."
RE_PARSE_ERROR = r"Parse Error\nUnexpected char"
RE_INSUFF_FUNDS = r"Assert Exception\nowner\.balance >= op\.balance: Insufficient funds\."
RE_COMMON_ERROR = r"Assert Exception"
RE_POSITIVE_BALANCE = r"Assert Exception\nbalance > asset\(0, SCORUM_SYMBOL\): Balance must be positive"
RE_DEADLINE_TIME = r"Assert Exception\n.* Deadline time must be greater or equal then start time"
RE_MISSING_AUTHORITY = r"Missing Active Authority"
RE_START_TIME = r"Assert Exception\n.* (Start time must be greater than|should start after) head block time"
RE_INVALID_UUID = r"invalid uuid string"
RE_NOT_MODERATOR = r" Assert Exception\n.* User .* isn\'t an? (advertising|betting) moderator\n"
MAX_INT_64 = 9223372036854775807


def check_logs_on_errors(logs):
    """
    Check given string on existence of common 'error keywords'.

    :param str logs:
    """
    m = re.search(RE_ERROR_KWDS, logs, re.IGNORECASE)
    assert m is None, "In logs presents error message: '%s'" % m.group().strip()


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


def check_virt_ops(wallet, start, stop, expected_ops):
    expected_ops = set(expected_ops)
    ops = set()
    data = []
    for i in range(start, stop + 1):
        response = wallet.get_ops_in_block(i)
        if response and 'error' not in response:
            ops.update(set(d['op'][0] for _, d in response))
            data += [d['op'] for _, d in response]
    assert len(ops.intersection(expected_ops)) == len(expected_ops), \
        "Some expected virtual operations are misssing:\nActual: %s\nExpected: %s" % (ops, expected_ops)
    return data


def is_operation_in_block(block, operation_name, operation_kwargs):
    for tr in block['transactions']:
        for op in tr['operations']:
            op_name = op[0]
            op_params = op[1]
            if op_name == operation_name:
                if all([op_params[key] == operation_kwargs[key] for key in operation_kwargs.keys()]):
                    return True
    return False


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


def validate_response(response, op, required_params=None):
    """
    Validate response of some API operation.

    :param dict response:  Response getting after sending request.
    :param str op:  Name of requested API function.
    :param list[str|tuple] required_params: List of required parametrs to be compared with.
        Example: ["param1", ("param2": int), ("param3": 12.3)]
        Provided checks:
            - "param1" is in response and value of "param1" has `str` type. Equivalent with ("param1", str) tuple
            - "param2" is in response and value of "param2" has `int` type
            - "param3" is in response, value of "param3" has `float` type and value == 12.3
    """

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
        expect(key in response, "Parameter '%s' is missing in '%s' response: %s" % (key, op, response))
        if key not in response:
            continue
        expect(
            isinstance(response[key], val_type),
            "Parameter '%s' of '%s' has invalid value type '%s', expected '%s': %s" %
            (key, op, type(response[key]), val_type, response)
        )
        if val_type == value or isinstance(response[key], val_type):
            continue
        expect(
            response[key] == value,
            "Parameter '%s' of '%s' has invalid value '%s', expected '%s': %s" %
            (key, op, response[key], value, response)
        )
    assert_expectations()


def validate_error_response(response, op: str, pattern=RE_COMMON_ERROR):
    err = response.get("error", {})
    m = re.search(pattern, err.get("message", ""), re.IGNORECASE)
    assert err and m is not None, \
        "%s operation should fail but passed with result: %s" % (op, err)


def apply_hardfork(wallet: Wallet, hf_id: int):
    assert hf_id > 0
    for i in range(1, hf_id + 1):
        wallet.get_block(i + 1, wait_for_block=True)
        wallet.debug_set_hardfork(i)
        wallet.get_block(i + 2, wait_for_block=True)
        assert wallet.debug_has_hardfork(i)


def gen_uid(unique: str=None):
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, unique)) if unique else str(uuid.uuid4())
