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


def test_serialize_game_type():
    assert to_hex(Game.hockey) == b'01'
    assert to_hex(Game.soccer) == b'00'


def test_serialize_markets():
    def market_to_hex(m):
        return to_hex(Market(m))

    assert market_to_hex(market.ResultHome()) == b'00'
    assert market_to_hex(market.ResultDraw()) == b'01'
    assert market_to_hex(market.ResultAway()) == b'02'
    assert market_to_hex(market.Round()) == b'03'
    assert market_to_hex(market.Handicap()) == b'040000'
    assert market_to_hex(market.CorrectScore()) == b'05'
    assert market_to_hex(market.CorrectScoreParametrized()) == b'0600000000'
    assert market_to_hex(market.Goal()) == b'07'
    assert market_to_hex(market.Total()) == b'080000'
    assert market_to_hex(market.TotalGoals()) == b'090000'
