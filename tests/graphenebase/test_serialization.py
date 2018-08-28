from binascii import hexlify

from graphenebase.types import BudgetType
from graphenebase.amount import Amount
from src.operations_fabric import devpool_withdraw_vesting, create_budget_operation


def test_serialize_banner_to_string():
    x = BudgetType("banner")
    assert str(x) == "banner"


def test_serialize_post_to_string():
    x = BudgetType("post")
    assert str(x) == "post"


def test_serialize_banner_to_byte():
    x = BudgetType("banner")
    assert hexlify(bytes(x)) == b'0100000000000000'


def test_serialize_post_to_byte():
    x = BudgetType("post")
    assert hexlify(bytes(x)) == b'0000000000000000'


def test_serialize_create_budget_to_byte():
    op = create_budget_operation(
        "initdelegate", "{}", Amount("10.000000000 SCR"), "2018-08-03T10:12:43", "2018-08-03T10:13:13", "post"
    )
    result_bin = b'00000000000000000c696e697464656c6567617465027b7d00e40b540200000009534352000000009b2a645bb92a645b'
    assert hexlify(bytes(op)) == result_bin


def test_serialize_devpool_withdraw_vesting_proposal_create():
    op = devpool_withdraw_vesting("initdelegate", Amount("10.000000000 SP"), 86400)
    result_bin = b'0c696e697464656c6567617465805101000600e40b54020000000953500000000000'
    # In C++   b'1d0c696e697464656c6567617465805101000600e40b54020000000953500000000000'
    # The difference is only at the beginning - in result_bin is missing '1d'.
    # That is hexlified id for ProposalCreate - hexlify(operationids.operations["proposal_create"])  == '1d'
    # those bytes are added in SignedTransaction.cast_operations_to_array_of_opklass
    assert hexlify(bytes(op)) == result_bin
