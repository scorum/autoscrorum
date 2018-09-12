import re
import json

from graphenebase.types import Id, Uint16, OrderedDict
from graphenebase.objects import GrapheneObject


MARKETS = [
    "result_home_market",
    "result_draw_market",
    "result_away_market",
    "round_market",
    "handicap_market",
    "correct_score_market",
    "correct_score_parametrized_market",
    "goal_market",
    "total_market",
    "total_goals_market",
]


class Market:
    def __init__(self, market_type):
        self.market_type = market_type
        self.name = self.get_market_name(market_type)
        self.id = self.get_market_id(self.name)

    @staticmethod
    def get_market_id(name: str):
        try:
            return MARKETS.index(name)
        except ValueError:
            raise Exception("no such market %s" % name)

    @staticmethod
    def get_market_name(market_type):
        """ Take a name of a class, like ResultHome and turn it into method name like result_home_market. """
        class_name = type(market_type).__name__  # also store name
        words = re.findall('[A-Z][^A-Z]*', class_name)

        return '_'.join(map(str.lower, words)) + "_market"

    def __bytes__(self):
        return bytes(Id(self.id)) + bytes(self.market_type)

    def __str__(self):
        return json.dumps([self.name, self.market_type.toJson()])


class ResultHome(GrapheneObject):
    pass


class ResultDraw(GrapheneObject):
    pass


class ResultAway(GrapheneObject):
    pass


class Round(GrapheneObject):
    pass


class Handicap(GrapheneObject):
    def __init__(self, threshold=0):
        self.data = OrderedDict({"threshold": Uint16(threshold)})

        super(Handicap, self).__init__(self.data)


class CorrectScore(GrapheneObject):
    pass


class CorrectScoreParametrized(GrapheneObject):
    def __init__(self, home=0, away=0):
        self.data = OrderedDict({"home": Uint16(home), "away": Uint16(away)})

        super(CorrectScoreParametrized, self).__init__(self.data)


class Goal(GrapheneObject):
    pass


class Total(GrapheneObject):
    def __init__(self, threshold=0):
        self.data = OrderedDict({"threshold": Uint16(threshold)})

        super(Total, self).__init__(self.data)


class TotalGoals(GrapheneObject):
    def __init__(self, threshold=0):
        self.data = OrderedDict({"threshold": Uint16(threshold)})

        super(TotalGoals, self).__init__(self.data)
