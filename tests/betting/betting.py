from scorum.graphenebase.amount import Amount
from scorum.graphenebase.betting import game, market, wincase
from scorum.utils.time import fmt_time_from_now

from tests.common import DEFAULT_WITNESS, gen_uid


class Bet:
    def __init__(self, account, wincase, odds, stake="1.000000000 SCR", live=True):
        self.account = account
        self.wincase = wincase
        self.odds = odds
        self.stake = Amount(stake)
        self.potential_reward = self.stake * odds[0] / odds[1]
        self.profit = self.potential_reward - self.stake
        self.uuid = None
        self.block_creation_num = None
        self.live = live


class Betting:
    def __init__(self, wallet, moderator=DEFAULT_WITNESS):
        self.wallet = wallet
        self.moderator = moderator

    def empower_betting_moderator(self):
        self.wallet.development_committee_empower_betting_moderator(DEFAULT_WITNESS, self.moderator)
        proposals = self.wallet.list_proposals()
        self.wallet.proposal_vote(DEFAULT_WITNESS, proposals[-1]["id"])

    def change_resolve_delay(self, delay=60):
        self.wallet.development_committee_change_betting_resolve_delay(DEFAULT_WITNESS, delay)
        proposals = self.wallet.list_proposals()
        self.wallet.proposal_vote(DEFAULT_WITNESS, proposals[-1]["id"])

    def create_game(self, account=DEFAULT_WITNESS, **kwargs):
        """
        'Additional_argument' default_value:
        ---
        'json_metadata' "{}"
        'start' 3
        'delay' 30
        'game_type' game.Soccer()
        'market_types' []
        """
        uuid = gen_uid()
        response = self.wallet.create_game(
            uuid, account,
            kwargs.get('json_metadata', "{}"),
            fmt_time_from_now(kwargs.get("start", 3)), kwargs.get("delay", 30),
            kwargs.get("game_type", game.Soccer()), kwargs.get("market_types", [])
        )
        return uuid, response['block_num']

    def post_bet(self, better, game_uuid, **kwargs):
        """
        'Additional_argument' default_value:
        ---
        'wincase_type' wincase.RoundHomeYes()
        'sodds' [3, 2]
        'stake' "1.000000000 SCR"
        'live' True
        """
        uuid = gen_uid()
        response = self.wallet.post_bet(
            uuid, better, game_uuid,
            kwargs.get("wincase_type", wincase.RoundHomeYes()),
            kwargs.get("odds", [3, 2]),
            kwargs.get("stake", "1.000000000 SCR"),
            kwargs.get("live", True)
        )
        return uuid, response['block_num']

    def post_bets_single_block(self, game_uuid, bets):
        for b in bets:
            b.uuid = gen_uid()
        data = [{
            "uuid": b.uuid, "better": b.account, "game_uuid": game_uuid, "wincase": b.wincase,
            "odds": b.odds, "stake": str(b.stake), "live": b.live
        } for b in bets]
        response = self.wallet.broadcast_multiple_ops("post_bet", data, set(b.account for b in bets))
        for bet in bets:
            bet.block_creation_num = response['block_num']

    def post_bets_sequentially(self, game_uuid, bets):
        for bet in bets:
            uuid, block = self.post_bet(
                bet.account, game_uuid,
                wincase_type=bet.wincase, odds=bet.odds,
                stake=str(bet.stake), live=bet.live
            )
            bet.uuid = uuid
            bet.block_creation_num = block

    def create_game_with_bets(self, bets, **kwargs):
        self.empower_betting_moderator()
        game_uuid, block = self.create_game(
            start=kwargs.get('game_start', 30), delay=kwargs.get('delay', 3600),
            market_types=kwargs.get('market_types', [market.RoundHome(), market.Handicap(500)]))
        if kwargs.get("single_block", True):
            self.post_bets_single_block(game_uuid, bets)
        else:
            self.post_bets_sequentially(game_uuid, bets)
        return game_uuid
