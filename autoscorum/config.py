from copy import deepcopy


class Config(object):
    def __init__(self):
        self.parms = {}

    def __getitem__(self, item):
        return self.parms[item]

    def __setitem__(self, key, value):
        self.parms[key] = value

    def __contains__(self, item):
        return item in self.parms

    def __copy__(self):
        new = Config()
        new.parms = deepcopy(self.parms)
        return new

    def get(self, key, default=None):
        return self.__getitem__(key) if self.__contains__(key) else default

    def dump(self):
        result = ''
        for key, value in self.parms.items():
            result += "{key} = {value}\n".format(key=key, value=value)
        return result

    def get_rpc_port(self):
        return self['rpc-endpoint'].split(':', 1)[1]


def test_dump():
    config = Config()
    config['parm1'] = 'value'
    config['parm2'] = 'value'
    expected_str = 'rpc-endpoint = 0.0.0.0:8090\n' \
                   'genesis-json = genesis.json\n' \
                   'enable-stale-production = true\n' \
                   'shared-file-size = 1G\n' \
                   'parm1 = value\n' \
                   'parm2 = value\n'
    assert config.dump() == expected_str


def test_get_rpc_port():
    config = Config()
    config['rpc-endpoint'] = '127.0.0.1:8090'
    assert config.get_rpc_port() == '8090'
