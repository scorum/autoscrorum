from binascii import hexlify

from graphenebase import operations
from graphenebase.types import BudgetType


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
    op = operations.CreateBudget(
        **{'owner': "initdelegate",
           'json_metadata': "{}",
           'balance': "10.000000000 SCR",
           'start': "2018-08-03T10:12:43",
           'deadline': "2018-08-03T10:13:13",
           'type': "post"})

    result_bin = b'00000000000000000c696e697464656c6567617465027b7d00e40b540200000009534352000000009b2a645bb92a645b'
    assert hexlify(bytes(op)) == result_bin


def test_serialize_proposal_create():
    op = operations.ProposalCreate(**{
        "creator": "initdelegate", "lifetime_sec": 86400,
        "op_data": {"vesting_shares": "10.000000000 SP"},
        "op_name": "development_committee_withdraw_vesting"
    })

    result_bin = b'00000000000000000c696e697464656c6567617465027b7d00e40b540200000009534352000000009b2a645bb92a645b'
    # result_bin = b'0c696e697464656c6567617465805101000631302e303030303030303030205350'
    assert hexlify(bytes(op)) == result_bin
