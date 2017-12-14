import time
import datetime
import json

class Genesis(object):
    def __init__(self):
        self.parms = {}
        self["init_supply"] = 1000
        self["accounts"] = []
        self["witness_candidates"] = []

    def __getitem__(self, item):
        return self.parms[item]

    def __setitem__(self, key, value):
        self.parms[key] = value

    def add_account(self, acc_name, public_key, recovery_account='', scr_amount=0, sp_amount=0,  witness=False):
        account = {"name": f"{acc_name}",
                   "recovery_account": f"{recovery_account}",
                   "public_key": f"{public_key}",
                   "scr_amount": scr_amount,
                   "sp_amount": sp_amount}

        self['accounts'].append(account)
        if witness:
            self.add_witness(self, account["name"], account[public_key])

    def add_witness(self, name, signing_key):
        witness = {"owner_name": f"{name}",
                   "block_signing_key": f"{signing_key}"}
        self["witness_candidates"].append(witness)

    def dump(self):
        return json.dumps(self.parms)

    def _set_timestamp(self):
        timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%S')
        self['initial_timestamp'] = f"{timestamp}"
