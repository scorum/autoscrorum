from graphenebase.account import PasswordKey


class Account(object):
    def __init__(self, name, password=None):
        self.name = name
        self._password = password if password else self.name

        self.owner = PasswordKey(self.name, self._password, role='owner')
        self.active = PasswordKey(self.name, self._password, role='active')
        self.posting = PasswordKey(self.name, self._password, role='posting')
        self.signing = None

    def __eq__(self, other):
        return self.name == other.name

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

    def set_signing_key(self):
        self.signing = PasswordKey(self.name, self._password, role='signing')
        return self
