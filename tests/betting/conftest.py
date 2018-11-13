from collections import defaultdict

import pytest
from scorum.graphenebase.amount import Amount
from scorum.graphenebase.betting import game, market, wincase
from scorum.utils.time import fmt_time_from_now

from tests.common import apply_hardfork, DEFAULT_WITNESS, gen_uid

GAME_FILTERS = [
    "created",
    "started",
    "finished",
    "resolved",
    "expired",
    "cancelled"
]


@pytest.fixture(scope="function")
def wallet_4hf(wallet):
    apply_hardfork(wallet, 4)
    return wallet


def empower_betting_moderator(wallet, account=DEFAULT_WITNESS):
    wallet.development_committee_empower_betting_moderator(DEFAULT_WITNESS, account)
    proposals = wallet.list_proposals()
    wallet.proposal_vote(DEFAULT_WITNESS, proposals[-1]["id"])


def change_resolve_delay(wallet, delay=60):
    wallet.development_committee_change_betting_resolve_delay(DEFAULT_WITNESS, delay)
    proposals = wallet.list_proposals()
    wallet.proposal_vote(DEFAULT_WITNESS, proposals[-1]["id"])


def create_game(wallet, account=DEFAULT_WITNESS, **kwargs):
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
    response = wallet.create_game(
        uuid, account,
        kwargs.get('json_metadata', kwargs.get("json_metadata", "{}")),
        fmt_time_from_now(kwargs.get("start", 3)), kwargs.get("delay", 30),
        kwargs.get("game_type", game.Soccer()), kwargs.get("market_types", [])
    )
    return uuid, response['block_num']


def post_bet(wallet, better, game_uuid, **kwargs):
    """
    'Additional_argument' default_value:
    ---
    'wincase_type' wincase.RoundHomeYes()
    'sodds' [3, 2]
    'stake' "1.000000000 SCR"
    'live' True
    """
    uuid = gen_uid()
    response = wallet.post_bet(
        uuid, better, game_uuid,
        kwargs.get("wincase_type", wincase.RoundHomeYes()),
        kwargs.get("odds", [3, 2]),
        kwargs.get("stake", "1.000000000 SCR"),
        kwargs.get("live", True)
    )
    return uuid, response['block_num']


class Bet:
    def __init__(self, account, wincase, odds, stake="1.000000000 SCR"):
        self.account = account
        self.wincase = wincase
        self.odds = odds
        self.stake = Amount(stake)
        self.potential_reward = self.stake * odds[0] / odds[1]
        self.profit = self.potential_reward - self.stake
        self.uuid = None
        self.block_creation_num = None


def create_game_with_bets(wallet, bets, **kwargs):
    empower_betting_moderator(wallet)
    game_uuid, block = create_game(
        wallet, start=kwargs.get('game_start', 30), delay=kwargs.get('delay', 3600),
        market_types=kwargs.get('market_types', [market.RoundHome(), market.Handicap(500)]))
    for bet in bets:
        uuid, block = post_bet(
            wallet, bet.account, game_uuid, wincase_type=bet.wincase, odds=bet.odds, stake=str(bet.stake)
        )
        bet.uuid = uuid
        bet.block_creation_num = block
    return game_uuid


@pytest.fixture(scope="function")
def matched_bets():
    return [Bet("alice", wincase.RoundHomeYes(), [3, 2]), Bet("bob", wincase.RoundHomeNo(), [3, 1])]


@pytest.fixture(scope="function")
def pending_bets():  # unmatched bets
    return [Bet("alice", wincase.RoundHomeYes(), [3, 2]), Bet("bob", wincase.HandicapOver(500), [5, 1])]


@pytest.fixture(params=['matched_bets', 'pending_bets'])
def bets(request):
    return request.getfixturevalue(request.param)


def sum_amount(amounts, start="0 SCR"):
    return sum([Amount(a) if isinstance(a, str) else a for a in amounts], Amount(start))


@pytest.fixture(scope="session")
def real_game_data():
    markets = [
        market.RoundHome(), market.ResultHome(),  market.Total(1000), market.Handicap(500),
        market.CorrectScore(3, 3), market.GoalAway()
    ]
    wincases = [
        wincase.RoundHomeYes(), wincase.ResultHomeYes(), wincase.TotalOver(1000), wincase.HandicapUnder(500),
        wincase.GoalAwayNo(), wincase.CorrectScoreYes(3, 3)
    ]

    bets = [
        # 1x1 full
        Bet("alice", wincase.RoundHomeYes(), [3, 2], "1.000000000 SCR"),  # winner
        Bet("bob", wincase.RoundHomeNo(), [3, 1], "0.500000000 SCR"),  # looser

        Bet("alice", wincase.RoundHomeNo(), [5, 2], "1.000000000 SCR"),  # looser
        Bet("bob", wincase.RoundHomeYes(), [5, 3], "1.500000000 SCR"),  # winner
        # 1x1 partial
        Bet("alice", wincase.ResultHomeYes(), [3, 2], "1.000000000 SCR"),  # winner
        Bet("bob", wincase.ResultHomeNo(), [3, 1], "1.000000000 SCR"),  # looser, remain pending 0.5 SCR

        Bet("alice", wincase.ResultHomeNo(), [5, 2], "1.000000000 SCR"),  # looser, remain pending 0.33.. SCR
        Bet("bob", wincase.ResultHomeYes(), [5, 3], "1.000000000 SCR"),  # winner
        # 1xN full
        Bet("test.test1", wincase.TotalOver(1000), [4, 1], "1.500000000 SCR"),  # winner
        Bet("test.test2", wincase.TotalUnder(1000), [4, 3], "1.500000000 SCR"),  # looser
        Bet("test.test3", wincase.TotalUnder(1000), [4, 3], "1.500000000 SCR"),  # looser
        Bet("test.test4", wincase.TotalUnder(1000), [4, 3], "1.500000000 SCR"),  # looser

        Bet("test.test1", wincase.TotalUnder(1000), [5, 3], "4.500000000 SCR"),  # looser
        Bet("test.test2", wincase.TotalOver(1000), [5, 2], "1.000000000 SCR"),  # winner
        Bet("test.test3", wincase.TotalOver(1000), [5, 2], "1.000000000 SCR"),  # winner
        Bet("test.test4", wincase.TotalOver(1000), [5, 2], "1.000000000 SCR"),  # winner
        # 1xN partial
        Bet("test.test1", wincase.GoalAwayNo(), [4, 1], "3.500000000 SCR"),  # winner, remain pending 0.5 SCR
        Bet("test.test2", wincase.GoalAwayYes(), [4, 3], "1.500000000 SCR"),  # looser
        Bet("test.test3", wincase.GoalAwayYes(), [4, 3], "1.500000000 SCR"),  # looser
        Bet("test.test4", wincase.GoalAwayYes(), [4, 3], "1.500000000 SCR"),  # looser

        Bet("test.test1", wincase.GoalAwayYes(), [5, 3], "4.500000000 SCR"),  # looser, remain pending 2.25 SCR
        Bet("test.test2", wincase.GoalAwayNo(), [5, 2], "0.500000000 SCR"),  # winner
        Bet("test.test3", wincase.GoalAwayNo(), [5, 2], "0.500000000 SCR"),  # winner
        Bet("test.test4", wincase.GoalAwayNo(), [5, 2], "0.500000000 SCR"),  # winner
        # Nx1 full
        Bet("test.test1", wincase.HandicapUnder(500), [4, 3], "1.500000000 SCR"),  # winner
        Bet("test.test2", wincase.HandicapUnder(500), [4, 3], "1.500000000 SCR"),  # winner
        Bet("test.test3", wincase.HandicapUnder(500), [4, 3], "1.500000000 SCR"),  # winner
        Bet("test.test4", wincase.HandicapOver(500), [4, 1], "1.500000000 SCR"),  # looser

        Bet("test.test1", wincase.HandicapOver(500), [5, 2], "1.000000000 SCR"),  # looser
        Bet("test.test2", wincase.HandicapOver(500), [5, 2], "1.000000000 SCR"),  # looser
        Bet("test.test3", wincase.HandicapOver(500), [5, 2], "1.000000000 SCR"),  # looser
        Bet("test.test4", wincase.HandicapUnder(500), [5, 3], "4.500000000 SCR"),  # winner
        # Nx1 partial
        Bet("test.test1", wincase.CorrectScoreYes(3, 3), [4, 3], "0.500000000 SCR"),  # winner
        Bet("test.test2", wincase.CorrectScoreYes(3, 3), [4, 3], "0.500000000 SCR"),  # winner
        Bet("test.test3", wincase.CorrectScoreYes(3, 3), [4, 3], "0.500000000 SCR"),  # winner
        Bet("test.test4", wincase.CorrectScoreNo(3, 3), [4, 1], "1.000000000 SCR"),  # looser, remain pending 0.5 SCR

        Bet("test.test1", wincase.CorrectScoreNo(3, 3), [5, 2], "0.500000000 SCR"),  # looser
        Bet("test.test2", wincase.CorrectScoreNo(3, 3), [5, 2], "0.500000000 SCR"),  # looser
        Bet("test.test3", wincase.CorrectScoreNo(3, 3), [5, 2], "0.500000000 SCR"),  # looser
        Bet("test.test4", wincase.CorrectScoreYes(3, 3), [5, 3], "4.500000000 SCR"),  # winner, remain pending 2.25 SCR
    ]

    betters = [b.account for b in bets]

    expected_balances_outgo = defaultdict(Amount)
    for b in bets:
        expected_balances_outgo[b.account] += b.stake

    expected_balances_income = {
        "alice": sum_amount(["1.500000000 SCR", "1.500000000 SCR", "0.333333334 SCR"]),
        "bob": sum_amount(["2.500000000 SCR", "0.500000000 SCR", "1.666666666 SCR"]),
        "test.test1": sum_amount([
            "6.000000000 SCR", "8.000000000 SCR", "2.250000000 SCR", "2.000000000 SCR", "0.666666666 SCR"
        ]),
        "test.test2": sum_amount(["2.500000000 SCR", "1.250000000 SCR", "2.000000000 SCR", "0.666666666 SCR"]),
        "test.test3": sum_amount(["2.500000000 SCR", "1.250000000 SCR", "2.000000000 SCR", "0.666666666 SCR"]),
        "test.test4": sum_amount([
            "2.500000000 SCR", "1.250000000 SCR", "7.500000000 SCR", "0.500000002 SCR", "6.000000000 SCR"
        ])
    }

    return {
        "bets": bets, "wincases": wincases, "betters": betters, "markets": markets,
        "expected_outgo": expected_balances_outgo, "expected_income": expected_balances_income
    }
