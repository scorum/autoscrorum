class Amount(dict):
    """ This class helps deal and calculate with the different assets on the
            chain.
        :param str amount_string: Amount string as used by the backend
            (e.g. "10 SCR")
    """

    def __init__(self, amount_string="0 SCR"):
        if isinstance(amount_string, Amount):
            self["amount"] = amount_string["amount"]
            self["asset"] = amount_string["asset"]
        elif isinstance(amount_string, str):
            self["amount"], self["asset"] = amount_string.split(" ")
            self['amount'] = int(self['amount'].replace('.', '').lstrip('0'))
        else:
            raise ValueError(
                "Need an instance of 'Amount' or a string with amount " +
                "and asset")

    @property
    def amount(self):
        return self["amount"]

    @property
    def symbol(self):
        return self["asset"]

    @property
    def asset(self):
        return self["asset"]

    def _to_string(self, prec):
        def insert_zeroes_at_start(string):
            multiplier = prec - len(string)
            string = ('0' * (multiplier + 1)) + string
            return string

        def add_dot_separator(string):
            list_to_insert = list(string)
            list_to_insert.insert(-prec, '.')
            string = ''.join(list_to_insert)
            return string

        amount_string = str(self.amount)
        if len(amount_string) < prec:
            amount_string = insert_zeroes_at_start(amount_string)
        return add_dot_separator(amount_string)

    def __str__(self):
        if self["asset"] == "SCR":
            prec = 9
        elif self["asset"] == "SP":
            prec = 9

        # default
        else:
            prec = 9
        return "{} {}".format(
            self._to_string(prec), self["asset"])

    def __float__(self):
        return self["amount"]

    def __int__(self):
        return self["amount"]

    def __add__(self, other):
        a = Amount(self)
        if isinstance(other, Amount):
            a["amount"] += other["amount"]
        else:
            a["amount"] += int(other)
        return a

    def __sub__(self, other):
        a = Amount(self)
        if isinstance(other, Amount):
            a["amount"] -= other["amount"]
        else:
            a["amount"] -= int(other)
        return a

    def __mul__(self, other):
        a = Amount(self)
        if isinstance(other, Amount):
            a["amount"] *= other["amount"]
        else:
            a["amount"] *= other
        return a

    def __floordiv__(self, other):
        a = Amount(self)
        if isinstance(other, Amount):
            raise Exception("Cannot divide two Amounts")
        else:
            a["amount"] //= other
        return a

    def __div__(self, other):
        a = Amount(self)
        if isinstance(other, Amount):
            raise Exception("Cannot divide two Amounts")
        else:
            '''
            need to use floordiv to get result type int
            '''
            a["amount"] //= other
        return a

    def __mod__(self, other):
        a = Amount(self)
        if isinstance(other, Amount):
            a["amount"] %= other["amount"]
        else:
            a["amount"] %= other
        return a

    def __pow__(self, other):
        a = Amount(self)
        if isinstance(other, Amount):
            a["amount"] **= other["amount"]
        else:
            a["amount"] **= other
        return a

    def __iadd__(self, other):
        if isinstance(other, Amount):
            self["amount"] += other["amount"]
        else:
            self["amount"] += other
        return self

    def __isub__(self, other):
        if isinstance(other, Amount):
            self["amount"] -= other["amount"]
        else:
            self["amount"] -= other
        return self

    def __imul__(self, other):
        if isinstance(other, Amount):
            self["amount"] *= other["amount"]
        else:
            self["amount"] *= other
        return self

    def __idiv__(self, other):
        if isinstance(other, Amount):
            assert other["asset"] == self["asset"]
            return self["amount"] / other["amount"]
        else:
            '''
            need to use floordiv to get result type int
            '''
            self["amount"] //= other
            return self

    def __ifloordiv__(self, other):
        if isinstance(other, Amount):
            self["amount"] //= other["amount"]
        else:
            self["amount"] //= other
        return self

    def __imod__(self, other):
        if isinstance(other, Amount):
            self["amount"] %= other["amount"]
        else:
            self["amount"] %= other
        return self

    def __ipow__(self, other):
        self["amount"] **= other
        return self

    def __lt__(self, other):
        if isinstance(other, Amount):
            return self["amount"] < other["amount"]
        else:
            return self["amount"] < int(other or 0)

    def __le__(self, other):
        if isinstance(other, Amount):
            return self["amount"] <= other["amount"]
        else:
            return self["amount"] <= int(other or 0)

    def __eq__(self, other):
        if isinstance(other, Amount):
            return self['amount'] == other['amount']
        else:
            return self["amount"] == int(other or 0)

    def __ne__(self, other):
        if isinstance(other, Amount):
            return self["amount"] != other["amount"]
        else:
            return self["amount"] != int(other or 0)

    def __ge__(self, other):
        if isinstance(other, Amount):
            return self["amount"] >= other["amount"]
        else:
            return self["amount"] >= int(other or 0)

    def __gt__(self, other):
        if isinstance(other, Amount):
            return self["amount"] > other["amount"]
        else:
            return self["amount"] > int(other or 0)

    __repr__ = __str__
    __truediv__ = __div__
    __truemul__ = __mul__
