import json

from .utils import fmt_time_from_now


class Genesis(object):
    def __init__(self):
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

    def add_account(self, acc_name, public_key, scr_amount='0.000000000 SRC', witness=False, committee=False):
        if len(self["registration_committee"]) < 1:
            committee = True
        account = {"name": acc_name,
                   "public_key": public_key,
                   "scr_amount": scr_amount}

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
