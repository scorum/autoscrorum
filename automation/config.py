from copy import deepcopy


class Config(object):
    def __init__(self):
        self.params = {}

    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, key, value):
        self.params[key] = value

    def __additem__(self, key, value):
        try:
            v = self.params.pop(key)
            if isinstance(v, list):
                v.append(value)
                self.__setitem__(key, v)
            else:
                self.__setitem__(key, [v, value])
        except KeyError:
            self.params[key] = value

    def __contains__(self, item):
        return item in self.params

    def __copy__(self):
        new = Config()
        new.params = deepcopy(self.params)
        return new

    def get(self, key, default=None):
        return self.__getitem__(key) if self.__contains__(key) else default

    def pop(self, key, default_value=None):
        return self.params.pop(key, default_value)

    def dump(self):
        return '\n'.join([
            "{key} = {value}".format(key=key, value=value)
            if isinstance(value, str)
            else '\n'.join(["{k} = {v}".format(k=key, v=v) for v in value])
            for key, value in self.params.items()
        ]) + '\n'

    def get_rpc_port(self):
        # set dummy port if config is empty
        return self.get('rpc-endpoint', "0.0.0.0:8001").split(':')[1]

    def read(self, file_path: str):
        """
        Reads existing config file to memory

        :param str file_path:
        """
        with open(file_path, "r") as f:
            for row in f:
                line = row.strip()
                if not line or line.startswith("#"):
                    continue
                key, value = line.split(" = ")
                self.__additem__(key, value)


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
