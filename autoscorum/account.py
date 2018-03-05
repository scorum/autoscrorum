from graphenebase import account


class Account(object):
    def __init__(self, name, password=None):
        self.name = name
        self._password = password if password else self.name
        self.owner = account.PasswordKey(self.name, self._password, role='owner')
        self.active = account.PasswordKey(self.name, self._password, role='active')
        self.posting = account.PasswordKey(self.name, self._password, role='posting')