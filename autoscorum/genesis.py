import json

from .utils import fmt_time_from_now
from .account import Account
from graphenebase.amount import Amount


class Genesis(object):
    def __init__(self):
        self._accounts = []
        self.accounts_supply = Amount()
        self.steemit_bounty_supply = Amount('0 SP')
        self.parms = {}
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
        self["registration_schedule"] = [{"stage": 1,
                                          "users": 4,
                                          "bonus_percent": 100},
                                         {"stage": 2,
                                          "users": 1,
                                          "bonus_percent": 75},
                                         {"stage": 3,
                                          "users": 1,
                                          "bonus_percent": 50},
                                         {"stage": 4,
                                          "users": 1,
                                          "bonus_percent": 25}
                                         ]
        self["registration_committee"] = []
        self["development_committee"] = []

    def __getitem__(self, item):
        return self.parms[item]

    def __setitem__(self, key, value):
        self.parms[key] = value

    def add_account(self, acc):
        account = acc if type(acc) is Account else Account(acc)
        self._accounts.append(account)
        return account

    def dump(self):
        for acc in self._accounts:
            print('\n HELLO!!!!!!')
            print(acc.get_scr_balance())
            print(acc.name)
            self.accounts_supply += acc.get_scr_balance()
            self.steemit_bounty_supply += acc.get_steem_bounty()
            account = {'name': acc.name,
                       'scr_amount': acc.get_scr_balance(),
                       'public_key': acc.get_owner_public()}
            self['accounts'].append(account)

            if acc.is_witness():
                self['witness_candidates'].append({'name': acc.name,
                                                   'block_signing_key': acc.get_signing_public()})

            if acc.is_founder():
                self['founders'].append({'name': acc.name,
                                         'sp_percent': acc.get_founder_percent()})

            if acc.is_dev_committee():
                self['development_committee'].append(acc.name)

            if acc.is_reg_committee():
                self['registration_committee'].append(acc.name)

            if acc.is_in_steem_bounty_program():
                self['steemit_bounty_accounts'].append({'name': acc.name,
                                                        'sp_amount': acc.get_sp_balance()})

        self['accounts_supply'] = str(self.accounts_supply)
        self['steemit_bounty_accounts_supply'] = str(self.steemit_bounty_supply)

        self['total_supply'] = str((Amount(self['accounts_supply']) +
                                    Amount(self['rewards_supply']) +
                                    Amount(self['registration_supply']) +
                                    Amount(self['founders_supply']) +
                                    Amount(self['steemit_bounty_accounts_supply']) +
                                    Amount(self['development_sp_supply']) +
                                    Amount(self['development_scr_supply'])))
        return json.dumps(self.parms)

    def _set_timestamp(self):
        self['initial_timestamp'] = fmt_time_from_now(1)

    def get_accounts(self):
        return self._accounts

    def accounts(self, accounts=[]):
        for account in accounts:
            self['accounts'].append({"name": account.name,
                                     "recovery_account": "",
                                     "public_key": account.get_owner_public(),
                                     "scr_amount": account.scr_balance})
            # if account.sp_balance:
