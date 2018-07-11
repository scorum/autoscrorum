import json
from collections import namedtuple

from graphenebase.amount import Amount
from .account import Account
from .utils import fmt_time_from_now

GenesisAccount = namedtuple("GenesisAccount", ["account", "amount"])


class Genesis(object):
    def __init__(self):
        self.genesis_accounts = []   # list(GenesisAccount))
        self.witness_candidates = []  # list(Account)
        self.founders = set()  # set((str, float))
        self.reg_committee = set()  # set(str)
        self.dev_committee = set()  # set(str)
        self.steemit_bounty_accounts = set()  # set(str)

        self.accounts_supply = Amount()
        self.steemit_bounty_supply = Amount('0 SP')
        self.params = {}
        self._set_timestamp()
        self["lock_withdraw_sp_until_timestamp"] = "2018-07-01T00:00:00"
        self["total_supply"] = "700.000000000 SCR"
        self["registration_supply"] = "100.000000000 SCR"
        self["registration_bonus"] = "0.000000100 SCR"
        self["accounts_supply"] = "100.000000000 SCR"
        self["rewards_supply"] = "100.000000000 SCR"
        self["founders_supply"] = "100.000000000 SP"
        self["steemit_bounty_accounts_supply"] = "100.000000000 SP"
        self["development_sp_supply"] = "100.000000000 SP"
        self["development_scr_supply"] = "100.000000000 SCR"
        self["accounts"] = []
        self["founders"] = []
        self["steemit_bounty_accounts"] = []
        self["witness_candidates"] = []
        self["registration_schedule"] = [
            {"stage": 1, "users": 24, "bonus_percent": 100},
            {"stage": 2, "users": 1, "bonus_percent": 75},
            {"stage": 3, "users": 1, "bonus_percent": 50},
            {"stage": 4, "users": 1, "bonus_percent": 25}
        ]
        self["registration_committee"] = []
        self["development_committee"] = []

    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, key, value):
        self.params[key] = value

    def add_account(self, name, balance="100.000000000 SCR"):
        amount = Amount(balance)
        account = self.get_account(name)
        if not account:
            account = name if type(name) is Account else Account(name)
            self.genesis_accounts.append(GenesisAccount(account, amount))

    def get_account(self, name):
        account = name if type(name) is Account else Account(name)
        for ga in self.genesis_accounts:
            if account == ga.account:
                return ga.account

    def add_witness_acc(self, name):
        account = self.get_account(name)
        if account:
            account.set_signing_key()
            print("Genesis signing key: %s" % account.get_active_private())
            self.witness_candidates.append(account)

    def add_founder_acc(self, name, percent: float):
        account = self.get_account(name)
        if account:
            self.founders.add((account.name, percent))

    def add_dev_committee_acc(self, name):
        account = self.get_account(name)
        if account:
            self.dev_committee.add(account.name)

    def add_reg_committee_acc(self, name):
        account = self.get_account(name)
        if account:
            self.reg_committee.add(account.name)

    def add_steemit_bounty_acc(self, name):
        account = self.get_account(name)
        if account:
            self.steemit_bounty_accounts.add(account.name)

    def calculate_supplies(self):
        # calculate accounts supply
        for ga in self.genesis_accounts:
            self.accounts_supply += ga.amount

            account = {'name': ga.account.name,
                       'scr_amount': str(ga.amount),
                       'public_key': ga.account.get_owner_public()}
            self['accounts'].append(account)
        self['accounts_supply'] = str(self.accounts_supply)
        # collect witnesses
        self['witness_candidates'] = [
            {'name': acc.name, 'block_signing_key': acc.get_signing_public()}
            for acc in self.witness_candidates
        ]
        # collect founders
        self['founders'] = [
            {'name': name, 'sp_percent': percent}
            for name, percent in self.founders
        ]
        # collect dev_committee
        self['development_committee'] = list(self.dev_committee)
        # collect reg_committee
        self['registration_committee'] = list(self.reg_committee)
        # calculate steemit_bounty supply
        bounty_per_acc = Amount(
            self['steemit_bounty_accounts_supply']
        ) / len(self.steemit_bounty_accounts)

        self['steemit_bounty_accounts'] = [
            {'name': acc, 'sp_amount': str(bounty_per_acc)}
            for acc in self.steemit_bounty_accounts
        ]
        self.steemit_bounty_supply = bounty_per_acc * len(
            self.steemit_bounty_accounts
        )
        self['steemit_bounty_accounts_supply'] = str(self.steemit_bounty_supply)
        # calculate total supply
        supplies = [
            'accounts_supply', 'rewards_supply', 'registration_supply',
            'founders_supply', 'steemit_bounty_accounts_supply',
            'development_sp_supply', 'development_scr_supply'
        ]
        total = Amount()
        for supply in supplies:
            total += Amount(self[supply])
        self['total_supply'] = str(total)

    def dump(self):
        return json.dumps(self.params)

    def _set_timestamp(self):
        self['initial_timestamp'] = fmt_time_from_now(1)

    def get_accounts(self):
        return [ga.account for ga in self.genesis_accounts]
