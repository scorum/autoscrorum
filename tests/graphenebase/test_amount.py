import pytest

from graphenebase.amount import Amount


@pytest.mark.parametrize('amount_string,expected', [('10.000000000 SCR', 10000000000),
                                                    ('0.002003045 SCR', 2003045),
                                                    ('1.234567890 SCR', 1234567890),
                                                    ('0.000000001 SCR', 1),
                                                    ('0.001 SCR', 1000000),
                                                    ('0 SCR', 0),
                                                    ('1.01 SCR', 1010000000)])
def test_init_amount(amount_string, expected):
    a = Amount(amount_string)
    assert a['amount'] == expected


@pytest.mark.parametrize('asset,expected', [("SCR", "SCR"),
                                            ("SP", "SP"),
                                            ("CUSTOM", "CUSTOM")])
def test_init_asset(asset, expected):
    a = Amount("1.000000000 {}".format(asset))
    assert a['asset'] == expected


def test_equals_amount_with_different_assets():
    a = Amount('1.000000000 SCR')
    b = Amount('1.000000000 SP')
    assert a == b
