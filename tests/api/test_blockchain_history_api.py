import pytest

from automation.wallet import Wallet
from tests.common import validate_response


@pytest.mark.parametrize('block_num', [1, 3, 5])
def test_get_ops_history(wallet: Wallet, block_num):
    wallet.get_block(block_num, wait_for_block=True)
    response = wallet.get_ops_history(-1, 100, 0)  # get all operations
    validate_response(response, wallet.get_ops_history.__name__)
    assert len(response) == block_num, "Each block should be provided 'producer_reward' operation."


@pytest.mark.parametrize('block_num', [1, 3, 5])
def test_get_ops_history_pagination(wallet: Wallet, block_num):
    wallet.get_block(block_num, wait_for_block=True)
    response = wallet.get_ops_history(1, 1, 0)  # get first operation
    validate_response(response, wallet.get_ops_history.__name__)
    assert len(response) == 1, "Should be returned single operation."
    assert response[0][0] == 0, "Should be returned first operation (with 'id' = 0)"


@pytest.mark.parametrize('block_num', [1, 3, 5])
def test_get_blocks(wallet: Wallet, block_num):
    wallet.get_block(block_num, wait_for_block=True)
    blocks = wallet.get_blocks(block_num, limit=block_num)
    validate_response(blocks, wallet.get_blocks.__name__)
    assert len(blocks) == block_num, "Should be returned %d blocks" % block_num
