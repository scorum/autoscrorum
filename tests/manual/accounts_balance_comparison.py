from automation.wallet import Wallet
from scorum.graphenebase.amount import Amount


CHAIN_ID = "d3c1f19a4947c296446583f988c43fd1a83818fabaf3454a0020198cb361ebd2"
node1 = "rpc-bet-pink-tnet-ams3-1.scorum.work:8001"
node2 = "rpc-pink-tnet-ams3-1.scorum.work:8001"


def get_all_accounts(address):
    with Wallet(CHAIN_ID, address) as wallet:
        accounts = wallet.get_accounts(wallet.list_all_accounts())
        return {a["name"]: a for a in accounts}


accs1 = get_all_accounts(node1)
accs2 = get_all_accounts(node2)

names = set(accs1.keys()).intersection(set(accs2))

assert names != {}, "There are no common accounts on two nodes."


for accs in [accs1, accs2]:
    skip = set(accs.keys()).difference(names)
    if skip:
        print("%d accounts will be skipped as they do not present in opposite node: %s" % (len(skip), skip))

print("Will be checked %d accounts" % len(names))

for name in names:
    for param in ["balance", "scorumpower"]:
        b1 = Amount(accs1[name][param])
        b2 = Amount(accs2[name][param])
        if b1 == b2:
            continue
        print(
            "For '%s'\'s account amount of '%s'  is different between two nodes: '%s' != '%s'" %
            (name, param, str(b1), str(b2))
        )
