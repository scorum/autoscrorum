class Config(object):
    def __init__(self, parms={}):
        self.parms = parms

    def __getitem__(self, item):
        return self.parms[item]

    def __setitem__(self, key, value):
        self.parms[key] = value

    def __copy__(self):
        return Config(self.parms)

    def dump(self):
        result = ''
        for key, value in self.parms.items():
            result += f"{key} = {value}\n"
        return result

    def get_rcp_port(self):
        return self['rpc-endpoint'].split(':', 1)[1]


def test_dump():
    config = Config()
    config['parm1'] = 'value'
    config['parm2'] = 'value'
    expected_str = 'parm1 = value\n' \
                   'parm2 = value\n'
    assert config.dump() == expected_str


def test_get_rcp_port():
    config = Config()
    config['rpc-endpoint'] = '127.0.0.1:8090'
    assert config.get_rcp_port() == '8090'
