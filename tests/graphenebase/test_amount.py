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


@pytest.mark.parametrize('values,result', [
    (("5.000000000 SP", "2.000000000 SP"), ("3.000000000 SP", 3000000000)),
    (("5.000000000 SP", "1.500000000 SP"), ("3.500000000 SP", 3500000000)),
    (("0.240000000 SP", "0.012000000 SP"), ("0.228000000 SP", 228000000)),
    (("2.000000000 SP", "5.000000000 SP"), ("-3.000000000 SP", -3000000000)),
    (("1.500000000 SP", "5.000000000 SP"), ("-3.500000000 SP", -3500000000)),
    (("0.012000000 SP", "0.240000000 SP"), ("-0.228000000 SP", -228000000))
])
def test_subtraction(values, result):
    a, b = values
    r_str, r_int = result
    sub = Amount(a) - Amount(b)
    assert sub["amount"] == r_int, "subtraction calculation is wrong."
    assert str(sub) == r_str, "subtraction string representation is wrong."


@pytest.mark.parametrize('values,result', [
    (("1.000000000 SP", 5), ("5.000000000 SP", 5000000000)),
    (("1.000000000 SP", 0.5), ("0.500000000 SP", 500000000)),
    (("1.000000000 SP", 10), ("10.000000000 SP", 10000000000)),
    (("1.000000000 SP", 0.001), ("0.001000000 SP", 1000000)),
    (("1.000000000 SP", -3), ("-3.000000000 SP", -3000000000)),
    (("1.000000000 SP", -0.03), ("-0.030000000 SP", -30000000))
])
def test_multiplication(values, result):
    a, b = values
    r_str, r_int = result
    mul = Amount(a) * b
    assert r_int == mul["amount"], "multiplication calculation is wrong."
    assert r_str == str(mul), "multiplication string representation is wrong."
