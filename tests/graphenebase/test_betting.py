import pytest

from binascii import hexlify

from graphenebase.betting import market
from graphenebase.betting import Game, Market
from graphenebase.operations import CreateGame


def to_hex(data):
    return hexlify(bytes(data))


def test_serialize_soccer_game_with_empty_markets():
    op = CreateGame(
        **{'moderator': "admin",
           'name': "game name",
           'start': "2018-08-03T10:12:43",
           'game': Game.soccer,
           'markets': []}
    )

    assert to_hex(op) == b'0561646d696e0967616d65206e616d659b2a645b0000'


def test_serialize_soccer_game_with_total_1000():
    op = CreateGame(
        **{'moderator': "admin",
           'name': "game name",
           'start': "2018-08-03T10:12:43",
           'game': Game.soccer,
           'markets': [market.Total(1000)]}
    )

    assert to_hex(op) == b'0561646d696e0967616d65206e616d659b2a645b000108e803'


def test_serialize_hockey_game_with_empty_markets():
    op = CreateGame(
        **{'moderator': "admin",
           'name': "game name",
           'start': "2018-08-03T10:12:43",
           'game': Game.hockey,
           'markets': []}
    )

    assert to_hex(op) == b'0561646d696e0967616d65206e616d659b2a645b0100'


@pytest.mark.parametrize('game,val', [(Game.hockey, b'01'),
                                      (Game.soccer, b'00')])
def test_serialize_game_type(game, val):
    assert to_hex(game) == val


@pytest.mark.parametrize('market_type, val', [(market.ResultHome, b'00'),
                                              (market.ResultDraw, b'01'),
                                              (market.ResultAway, b'02'),
                                              (market.Round, b'03'),
                                              (market.Handicap, b'040000'),
                                              (market.CorrectScore, b'05'),
                                              (market.CorrectScoreParametrized, b'0600000000'),
                                              (market.Goal, b'07'),
                                              (market.Total, b'080000'),
                                              (market.TotalGoals, b'090000')])
def test_serialize_markets(market_type, val):
    assert to_hex(Market(market_type())) == val
