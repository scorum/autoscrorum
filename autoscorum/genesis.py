import json

from .utils import fmt_time_from_now
from graphenebase.amount import Amount


class Genesis(object):
    def __init__(self):
        self.accounts_supply = Amount()
        self.rewards_supply = Amount()
        self.founders_supply = Amount('0 SP')
        self.steemit_bounty_supply = Amount('0 SP')
        self.registration_supply = Amount('0 SP')
        self.parms = {}
        self._set_timestamp()
        self["accounts_supply"] = "1000.000000000 SCR"
        self["rewards_supply"] = "100.000000000 SCR"

        self["accounts"] = []

        self["witness_candidates"] = []

        self["founders_supply"] = "100.000000000 SP"
        self["founders"] = []

        self["steemit_bounty_accounts_supply"] = "0.000000000 SP"
        self["steemit_bounty_accounts"] = []

        self["registration_committee"] = []
        self["registration_supply"] = "100.000000000 SCR"
        self["registration_bonus"] = "0.000000100 SCR"
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

    def __getitem__(self, item):
        return self.parms[item]

    def __setitem__(self, key, value):
        self.parms[key] = value

    def add_account(self, acc_name, public_key, recovery_account="", scr_amount='0.000000000 SRC', sp_amount='0.000000000 SP',  witness=False, committee=False):
        if len(self["registration_committee"]) < 1:
            committee = True
        account = {"name": acc_name,
                   "recovery_account": recovery_account,
                   "public_key": public_key,
                   "scr_amount": scr_amount,
                   "sp_amount": sp_amount}

        self['accounts'].append(account)
        if witness:
            self.add_witness(account["name"], account["public_key"])
        if committee:
            self["registration_committee"].append(account['name'])

    def add_witness(self, name, signing_key):
        witness = {"name": name,
                   "block_signing_key": signing_key}
        self["witness_candidates"].append(witness)

    def dump(self):
        return json.dumps(self.parms)

    def _set_timestamp(self):
        self['initial_timestamp'] = fmt_time_from_now(1)

    def accounts(self, accounts=[]):
        for account in accounts:
            self['accounts'].append({"name": account.name,
                                     "recovery_account": "",
                                     "public_key": account.get_owner_public(),
                                     "scr_amount": account.scr_balance})
            # if account.sp_balance:
