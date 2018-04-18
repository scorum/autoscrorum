from graphenebase.account import PasswordKey
from graphenebase.amount import Amount


class Account(object):
    def __init__(self, name, password=None):
        self.name = name
        self._password = password if password else self.name

        self.owner = PasswordKey(self.name, self._password, role='owner')
        self.active = PasswordKey(self.name, self._password, role='active')
        self.posting = PasswordKey(self.name, self._password, role='posting')
        self.signing = None

        self.reg_committee_member = False
        self.dev_committee_member = False
        self._scr_balance = Amount('0 SCR')
        self._sp_balance = Amount('0 SP')
        self._steem_bounty = Amount('0 SP')
        self._founder_percent = None

    def get_active_public(self):
        return str(self.active.get_public())

    def get_active_private(self):
        return str(self.active.get_private())

    def get_owner_public(self):
        return str(self.owner.get_public())

    def get_owner_private(self):
        return str(self.owner.get_private())

    def get_posting_public(self):
        return str(self.posting.get_public())

    def get_posting_private(self):
        return str(self.posting.get_private())

    def get_signing_public(self):
        return str(self.signing.get_public())

    def get_signing_private(self):
        return str(self.signing.get_private())

    def witness(self):
        self.signing = PasswordKey(self.name, self._password, role='signing')
        return self

    def is_witness(self):
        if self.signing:
            return True
        return False

    def founder(self, percent):
        self._founder_percent = percent
        return self

    def is_founder(self):
        if self._founder_percent:
            return True
        return False

    def get_founder_percent(self):
        if self.is_founder():
            return self._founder_percent
        return 0

    def dev_committee(self):
        self.dev_committee_member = True
        return self

    def is_dev_committee(self):
        return self.dev_committee_member

    def reg_committee(self):
        self.reg_committee_member = True
        return self

    def is_reg_committee(self):
        return self.reg_committee_member

    def steem_bounty(self, sp_bounty):
        self._steem_bounty = sp_bounty if type(sp_bounty) is Amount else Amount(sp_bounty)
        self._sp_balance += self._steem_bounty
        return self

    def get_steem_bounty(self):
        return self._steem_bounty

    def is_in_steem_bounty_program(self):
        if self._steem_bounty > 0:
            return True
        return False

    def scr_balance(self, balance):
        self._scr_balance = balance if type(balance) is Amount else Amount(balance)
        return self

    def get_src_balance(self):
        return self._scr_balance

    def sp_balance(self, balance):
        self._sp_balance = balance if type(balance) is Amount else Amount(balance)
        return self

    def get_sp_balance(self):
        return self._sp_balance
