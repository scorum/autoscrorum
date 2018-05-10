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
        self.scr_balance = Amount('0 SCR')
        self.sp_balance = Amount('0 SP')
        self.steem_bounty = Amount('0 SP')
        self.founder_percent = None

    def get_active_public(self):
        return str(self.owner.get_public())
        # return str(self.active.get_public())

    def get_active_private(self):
        return str(self.owner.get_private())
        # return str(self.active.get_private())

    def get_owner_public(self):
        return str(self.owner.get_public())

    def get_owner_private(self):
        return str(self.owner.get_private())

    def get_posting_public(self):
        return str(self.owner.get_public())
        # return str(self.posting.get_public())

    def get_posting_private(self):
        return str(self.owner.get_private())
        # return str(self.posting.get_private())

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
        self.founder_percent = percent
        return self

    def is_founder(self):
        if self.founder_percent:
            return True
        return False

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

    def steemit_bounty(self, sp_bounty):
        self.steem_bounty = sp_bounty if type(sp_bounty) is Amount else Amount(sp_bounty)
        self.sp_balance = self.steem_bounty
        return self

    def is_in_steem_bounty_program(self):
        if self.steem_bounty > 0:
            return True
        return False

    def set_scr_balance(self, balance):
        self.scr_balance = balance if type(balance) is Amount else Amount(balance)
        return self

    def set_sp_balance(self, balance):
        self.sp_balance = balance if type(balance) is Amount else Amount(balance)
        return self
