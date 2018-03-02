from collections import OrderedDict
import json
import struct
from .types import (
    Uint8, Int16, Uint16, Uint32, Uint64,
    Varint32, Int64, String, Bytes, Void,
    Array, PointInTime, Signature, Bool,
    Set, Fixed_array, Optional, Static_variant,
    Map, Id, VoteId, ObjectId,
)
from .objects import GrapheneObject, isArgsThisClass
from .account import PublicKey
from .chains import default_prefix
from .objects import Operation
from .operationids import operations

asset_precision = {
    "SCR": 9,
    "SP": 9,
}


class Amount:
    def __init__(self, d):
        self.amount, self.asset = d.strip().split(" ")
        self.amount = float(self.amount)

        if self.asset in asset_precision:
            self.precision = asset_precision[self.asset]
        else:
            raise Exception("Asset unknown")

    def __bytes__(self):
        # padding
        asset = self.asset + "\x00" * (7 - len(self.asset))
        amount = round(float(self.amount) * 10 ** self.precision)
        return (
            struct.pack("<q", amount) +
            struct.pack("<b", self.precision) +
            bytes(asset, "ascii")
        )

    def __str__(self):
        return '{:.{}f} {}'.format(
            self.amount,
            self.precision,
            self.asset
        )


class Permission(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            prefix = kwargs.pop("prefix", "SCR")

            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]

            # Sort keys (FIXME: ideally, the sorting is part of Public
            # Key and not located here)
            kwargs["key_auths"] = sorted(
                kwargs["key_auths"],
                key=lambda x: repr(PublicKey(x[0], prefix=prefix)),
                reverse=False,
            )
            kwargs["account_auths"] = sorted(
                kwargs["account_auths"],
                key=lambda x: x[0],
                reverse=False,
            )

            accountAuths = Map([
                [String(e[0]), Uint16(e[1])] for e in kwargs["account_auths"]
            ])
            keyAuths = Map([
                [PublicKey(e[0], prefix=prefix), Uint16(e[1])] for e in kwargs["key_auths"]
            ])
            super().__init__(OrderedDict([
                ('weight_threshold', Uint32(int(kwargs["weight_threshold"]))),
                ('account_auths', accountAuths),
                ('key_auths', keyAuths),
            ]))


class Demooepration(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
                self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(OrderedDict([
                ('string', String(kwargs["string"], "account")),
                ('extensions', Set([])),
            ]))


class CreateBudget(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('owner', String(kwargs["owner"])),
                    ('content_permlink', String(kwargs["content_permlink"])),
                    ('balance', Amount(kwargs["balance"])),
                    ('deadline', PointInTime(kwargs['deadline']))
                ]))


class Transfer(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            if "memo" not in kwargs:
                kwargs["memo"] = ""
            super().__init__(OrderedDict([
                ('from', String(kwargs["from"])),
                ('to', String(kwargs["to"])),
                ('amount', Amount(kwargs["amount"])),
                ('memo', String(kwargs["memo"])),
            ]))


class TransferToVesting(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('from', String(kwargs["from"])),
                    ('to', String(kwargs["to"])),
                    ('amount', Amount(kwargs["amount"])),
                ]))


class AccountCreate(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            prefix = kwargs.pop("prefix", default_prefix)

            meta = ""
            if "json_metadata" in kwargs and kwargs["json_metadata"]:
                if isinstance(kwargs["json_metadata"], dict):
                    meta = json.dumps(kwargs["json_metadata"])
                else:
                    meta = kwargs["json_metadata"]
            super().__init__(OrderedDict([
                ('fee', Amount(kwargs["fee"])),
                ('creator', String(kwargs["creator"])),
                ('new_account_name', String(kwargs["new_account_name"])),
                ('owner', Permission(kwargs["owner"], prefix=prefix)),
                ('active', Permission(kwargs["active"], prefix=prefix)),
                ('posting', Permission(kwargs["posting"], prefix=prefix)),
                ('memo_key', PublicKey(kwargs["memo_key"], prefix=prefix)),
                ('json_metadata', String(meta)),
            ]))


class AccountCreateByCommittee(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            prefix = kwargs.pop("prefix", default_prefix)

            meta = ""
            if "json_metadata" in kwargs and kwargs["json_metadata"]:
                if isinstance(kwargs["json_metadata"], dict):
                    meta = json.dumps(kwargs["json_metadata"])
                else:
                    meta = kwargs["json_metadata"]
            super().__init__(OrderedDict([
                ('creator', String(kwargs["creator"])),
                ('new_account_name', String(kwargs["new_account_name"])),
                ('owner', Permission(kwargs["owner"], prefix=prefix)),
                ('active', Permission(kwargs["active"], prefix=prefix)),
                ('posting', Permission(kwargs["posting"], prefix=prefix)),
                ('memo_key', PublicKey(kwargs["memo_key"], prefix=prefix)),
                ('json_metadata', String(meta)),
            ]))


class AccountWitnessVote(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('account', String(kwargs["account"])),
                    ('witness', String(kwargs["witness"])),
                    ('approve', Bool(bool(kwargs["approve"]))),
                ]))
