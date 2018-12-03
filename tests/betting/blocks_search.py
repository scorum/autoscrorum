import json

from scorum.graphenebase.betting import wincase

from automation.wallet import Wallet


def reverse(odds):
    return {"numerator": odds['numerator'], "denominator": odds['numerator'] - odds['denominator']}


class BetMatchingChecker(object):
    def __init__(self, blocks):
        self.blocks = blocks
        self.bets = []

    def remove_bet(self, uuid):
        self.bets = [b for b in self.bets if b['uuid'] != uuid]

    def get_bet(self, uuid):
        for b in self.bets:
            if b['uuid'] == uuid:
                return b

    def get_opposite_bets(self, bet):
        opposite_wc = wincase.create_obj_from_json([wincase.opposite(bet['wincase'][0]), bet['wincase'][1]])
        return sorted([
            b for b in self.bets
            if b['game_uuid'] == bet['game_uuid']
               and wincase.create_obj_from_json(b['wincase']) == opposite_wc
               and b['odds'] == reverse(bet['odds'])
        ], key=lambda x: x['block_num'])

    def check_matching_order(self, bet1, bet2):
        opposites = self.get_opposite_bets(bet1)
        expected = opposites[0]
        if opposites[0]['uuid'] != bet2['uuid']:
            print("Game '%s'" % bet1['game_uuid'])
            print("ERROR: for bet '%d':'%s' exist older bet '%d':'%s' but it was matched with '%d':'%s'" % (
                bet1['block_num'], bet1['uuid'],
                expected['block_num'], expected['uuid'],
                bet2['block_num'], bet2['uuid']
            ))

    def run(self):
        for block in self.blocks:
            if block['block_num'] < 6857122:
                continue
            for o in block['operations']:
                if o['op'][0] == "post_bet":
                    bet = o['op'][1]
                    bet['block_num'] = block['block_num']
                    self.bets.append(bet)
                if o['op'][0] == "bet_cancelled":
                    self.remove_bet(o['op'][1]['bet_uuid'])
                if o['op'][0] == "bets_matched":
                    bet1 = self.get_bet(o['op'][1]['bet1_uuid'])
                    bet2 = self.get_bet(o['op'][1]['bet2_uuid'])
                    self.check_matching_order(bet1, bet2)
                    self.check_matching_order(bet2, bet1)


if __name__ == "__main__":
    # chain_id = "db4007d45f04c1403a7e66a5c66b5b1cdfc2dde8b5335d1d2f116d592ca3dbb1"
    # address = "rpc-up-white-mnet-fra1-2.scorum.work:8001"

    chain_id = "d3c1f19a4947c296446583f988c43fd1a83818fabaf3454a0020198cb361ebd2"
    address = "rpc-pink-tnet-ams3-1.scorum.work:8001"

    dump_file = "testnet_blocks.json"
    start = 114153
    stop = 35060

    with Wallet(chain_id, address) as wallet:
        blocks = wallet.collect_blocks(start, stop)

    with open(dump_file, 'w') as f:
        f.write(json.dumps(sorted(blocks, key=lambda x: x['block_num'])))

    with open(dump_file, "r") as f:
        blocks = sorted(json.loads(f.read()), key=lambda x: x['block_num'])

    checker = BetMatchingChecker(blocks)
    checker.run()
