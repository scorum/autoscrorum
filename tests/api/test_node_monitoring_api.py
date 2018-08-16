from src.node import Node
from src.wallet import Wallet
from tests.common import check_logs_on_errors


def test_node_monitoring_api_crash(wallet: Wallet, node: Node):
    result = wallet.get_last_block_duration_in_microseconds()
    assert type(result) is int
    node.read_logs()
    check_logs_on_errors(node.logs)
