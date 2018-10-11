from collections import OrderedDict
import json
import struct
from .types import (
    Uint8, Int16, Uint16, Uint32, Uint64,
    Varint32, Int64, String, Bytes, Void,
    Array, PointInTime, Signature, Bool,
    Set, Fixed_array, Optional, Static_variant,
    Map, Id, VoteId, ObjectId, BudgetType, Uuid
)
from .objects import GrapheneObject, isArgsThisClass
from .account import PublicKey
from .chains import default_prefix
from .objects import Operation
from .operationids import operations

from .betting import Game, Market

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
                    ('type', BudgetType(kwargs['type'])),
                    ('uuid', Uuid(kwargs['uuid'])),
                    ('owner', String(kwargs["owner"])),
                    ('json_metadata', String(kwargs["json_metadata"])),
                    ('balance', Amount(kwargs["balance"])),
                    ('start', PointInTime(kwargs['start'])),
                    ('deadline', PointInTime(kwargs['deadline']))
                ]))


class CloseBudget(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('type', BudgetType(kwargs['type'])),
                    ('budget_id', Int64(kwargs['id'])),
                    ('owner', String(kwargs['owner'])),
                ]))


class UpdateBudget(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('type', BudgetType(kwargs['type'])),
                    ('budget_id', Int64(kwargs['id'])),
                    ('owner', String(kwargs['owner'])),
                    ('json_metadata', String(kwargs['json_metadata'])),
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


class TransferToScorumpower(GrapheneObject):
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


class WithdrawScorumpower(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('account', String(kwargs['account'])),
                    ('scorumpower', Amount(kwargs['scorumpower']))
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


class ProposalCreate(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('creator', String(kwargs['creator'])),
                    ('lifetime_sec', Uint32(kwargs['lifetime_sec'])),
                    ('operation', Operation(kwargs['operation']))
                ]))


class ProposalVote(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('voting_account', String(kwargs['voting_account'])),
                    ('proposal_id', Int64(kwargs['proposal_id']))
                ]))


class DevelopmentCommitteeWithdrawVesting(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('vesting_shares', Amount(kwargs['amount']))
                ]))


class DevelopmentCommitteeEmpowerAdvertisingModerator(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('account', String(kwargs['account']))
                ]))


class DevelopmentCommitteeChangePostBudgetsAuctionProperties(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('auction_coefficients', Array([Uint16(c) for c in kwargs['coeffs']]))
                ]))


class DevelopmentCommitteeChangeBannerBudgetsAuctionProperties(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('auction_coefficients', Array([Uint16(c) for c in kwargs['coeffs']]))
                ]))


class WitnessProps(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super(WitnessProps, self).__init__(
                OrderedDict([
                    ('account_creation_fee', Amount(kwargs["account_creation_fee"])),
                    ('maximum_block_size', Uint32(kwargs["maximum_block_size"])),
                ]))


class WitnessUpdate(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            prefix = kwargs.pop("prefix", default_prefix)

            if not kwargs["block_signing_key"]:
                kwargs[
                    "block_signing_key"] = \
                    "SCR1111111111111111111111111111111114T1Anm"
            super(WitnessUpdate, self).__init__(
                OrderedDict([
                    ('owner', String(kwargs["owner"])),
                    ('url', String(kwargs["url"])),
                    ('block_signing_key', PublicKey(kwargs["block_signing_key"], prefix=prefix)),
                    ('props', WitnessProps(kwargs["props"])),
                ]))


class Vote(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super(Vote, self).__init__(
                OrderedDict([
                    ('voter', String(kwargs["voter"])),
                    ('author', String(kwargs["author"])),
                    ('permlink', String(kwargs["permlink"])),
                    ('weight', Int16(kwargs["weight"])),
                ]))


class Comment(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            meta = ""
            if "json_metadata" in kwargs and kwargs["json_metadata"]:
                if (isinstance(kwargs["json_metadata"], dict)
                        or isinstance(kwargs["json_metadata"], list)):
                    meta = json.dumps(kwargs["json_metadata"])
                else:
                    meta = kwargs["json_metadata"]

            super(Comment, self).__init__(
                OrderedDict([
                    ('parent_author', String(kwargs["parent_author"])),
                    ('parent_permlink', String(kwargs["parent_permlink"])),
                    ('author', String(kwargs["author"])),
                    ('permlink', String(kwargs["permlink"])),
                    ('title', String(kwargs["title"])),
                    ('body', String(kwargs["body"])),
                    ('json_metadata', String(meta)),
                ]))


class DelegateScorumPower(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super(DelegateScorumPower, self).__init__(
                OrderedDict([
                    ('delegator', String(kwargs["delegator"])),
                    ('delegatee', String(kwargs["delegatee"])),
                    ('scorumpower', Amount(kwargs["scorumpower"])),
                ]))


class CreateGame(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]

            markets = [Market(m) for m in kwargs['markets']]

            super().__init__(
                OrderedDict([
                    ('moderator', String(kwargs['moderator'])),
                    ('name', String(kwargs["name"])),
                    ('start', PointInTime(kwargs['start'])),
                    ('game', Game(kwargs['game'])),
                    ('markets', Array(markets))
                ]))


class CloseBudgetByAdvertisingModerator(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict([
                    ('type', BudgetType(kwargs['type'])),
                    ('budget_id', Int64(kwargs["budget_id"])),
                    ('moderator', String(kwargs["moderator"]))
                ]))
