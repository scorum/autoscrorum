from enum import Enum


class Errors(Enum):
    assert_exception = 10
    tx_missing_active_auth = 3010000
    uniqueness_constraint_violated = 13
