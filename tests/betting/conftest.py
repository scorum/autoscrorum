from collections import defaultdict

import pytest
from scorum.graphenebase.amount import Amount
from scorum.graphenebase.betting import market, wincase, Market

from tests.common import apply_hardfork
from tests.betting.betting import Bet, Betting

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


@pytest.fixture(scope="function")
def betting(wallet_4hf):
    betting = Betting(wallet_4hf)
    betting.empower_betting_moderator()
    return betting


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
        market.CorrectScore(3, 3), market.GoalAway(), market.Handicap(), market.Total(2000)
    ]
    wincases = [
        wincase.RoundHomeYes(), wincase.ResultHomeYes(), wincase.TotalOver(1000), wincase.HandicapUnder(500),
        wincase.GoalAwayNo(), wincase.CorrectScoreYes(3, 3)
        # Handicap() and Total(2000) are not included to test payback
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

        # returns / paybacks
        Bet("alice", wincase.HandicapOver(), [3, 2], "1.000000000 SCR"),  # payback
        Bet("bob", wincase.HandicapUnder(), [3, 1], "0.500000000 SCR"),  # payback

        Bet("alice", wincase.TotalOver(2000), [2, 1], "1.000000000 SCR"),  # payback
        Bet("bob", wincase.TotalUnder(2000), [2, 1], "1.000000000 SCR"),  # payback

    ]

    betters = [b.account for b in bets]

    expected_resolved_ops = 24  # bets winners + paybacks

    expected_balances_outgo = defaultdict(Amount)
    for b in bets:
        expected_balances_outgo[b.account] += b.stake

    expected_paybacks = {
        str(Market(markets[6])): {
            "alice": "1.000000000 SCR",
            "bob": "0.500000000 SCR"
        },
        str(Market(markets[7])): {
            "alice": "1.000000000 SCR",
            "bob": "1.000000000 SCR"
        }
    }

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

    for v in expected_paybacks.values():
        for acc, amount in v.items():
            expected_balances_income[acc] += Amount(amount)

    return {
        "bets": bets, "wincases": wincases, "betters": betters, "markets": markets,
        "expected_paybacks": expected_paybacks,  "expected_outgo": expected_balances_outgo,
        "expected_income": expected_balances_income, "expected_resolved_ops": expected_resolved_ops
    }
