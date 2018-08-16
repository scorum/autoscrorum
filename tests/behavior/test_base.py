from graphenebase.amount import Amount
from src.genesis import Genesis
from src.node import Node
from src.wallet import Wallet
from tests.common import check_logs_on_errors, check_file_creation, generate_blocks


def test_node_logs(node, wallet):
    """
    Check logs of running node (logs are created, updated, there are no errors).

    :param Node node: Running node
    :param Wallet wallet: Wallet client to communicate with node
    """
    check_file_creation(node.logs_path)
    prev_size = 0
    for i in range(1, 5):  # or any max number of blocks
        wallet.get_block(i, wait_for_block=True)
        node.read_logs()
        curr_size = len(node.logs)
        assert curr_size > prev_size, "Node logs are not updated."
        prev_size = curr_size
        check_logs_on_errors(node.logs)


def test_block_production(wallet: Wallet, node: Node):
    block = wallet.get_block(1, wait_for_block=True)

    assert block['witness'] == node.config['witness'][1:-1]


def test_genesis_block(wallet: Wallet, genesis: Genesis):
    info = wallet.get_dynamic_global_properties()

    records = [
        'accounts_supply', 'rewards_supply', 'registration_supply',
        'founders_supply', 'steemit_bounty_accounts_supply',
        'development_sp_supply', 'development_scr_supply'
    ]

    expected_total_supply = Amount()

    for r in records:
        expected_total_supply = expected_total_supply + Amount(genesis[r])

    assert Amount(info['total_supply']) == expected_total_supply

    for account, amount in genesis.genesis_accounts:
        assert wallet.get_account_scr_balance(account.name) == amount


MIN_BLOCKS_TO_SAVE_INDEX = 21


def test_replay_blockchain(config, genesis, docker):
    """
    Test replay state of Node.

    :param Config config: Base config to run witness node
    :param Genesis genesis: Base genesis structure (users, accounts)
    :param DockerController docker: Pre-initialized image to run node
    """

    blocks_num = 5
    node = Node(config=config, genesis=genesis)
    node.generate_configs()
    # Start node, generate initial blocks in chain
    last_block = generate_blocks(
        node, docker, blocks_num + MIN_BLOCKS_TO_SAVE_INDEX
    )  # node was stopped
    assert last_block > 0, "Was not generated any block."

    node.drop_database()
    node.config['replay-blockchain'] = 'true'
    node.generate_configs()
    # Start node again, get header block
    last_block = generate_blocks(node, docker)  # node was stopped
    assert last_block >= blocks_num, \
        "Was generated %s blocks, should be >= %s" % (last_block, blocks_num)
    node.read_logs()
    check_logs_on_errors(node.logs)


def test_restart_node(config, genesis, docker):
    """
    Test restart of the node.

    :param Config config: Base config to run witness node
    :param Genesis genesis: Base genesis structure (users, accounts)
    :param DockerController docker: Pre-initialized image to run node
    """

    blocks_num = 5
    node = Node(config=config, genesis=genesis)
    node.generate_configs()
    # Start node, generate initial blocks in chain
    last_block = generate_blocks(
        node, docker, blocks_num + MIN_BLOCKS_TO_SAVE_INDEX
    )  # node was stopped
    assert last_block > 0, "Was not generated any block."
    # Start node again, get header block
    last_block = generate_blocks(node, docker)  # node was stopped
    assert last_block >= blocks_num, \
        "Was generated %s blocks, should be >= %s" % (last_block, blocks_num)
    node.read_logs()
    check_logs_on_errors(node.logs)
