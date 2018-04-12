from graphenebase import account


class Account(object):
    def __init__(self, name, password=None):
        self.name = name
        self._password = password if password else self.name
        self.owner = account.PasswordKey(self.name, self._password, role='owner')
        self.active = account.PasswordKey(self.name, self._password, role='active')
        self.posting = account.PasswordKey(self.name, self._password, role='posting')

        self.scr_balance = None
        self.sp_balance = None

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
