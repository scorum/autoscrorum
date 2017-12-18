import time
from steembase.http_client import HttpClient


class RpcClient(object):
    def __init__(self, nodes):
        addrs = []
        for node in nodes:
            addrs.append(node.addr)

        self._rpc = HttpClient(addrs, num_pools=1, retries=1, timeout=1)

    def get_block(self, num):
        result = None
        retry_count = 0
        while retry_count < 10:
            retry_count += 1
            result = self._rpc.exec('get_block', str(num))
            if result:
                break
            time.sleep(0.2)
        return result

    def get_account(self, name):
        return self._rpc.exec('get_account', name)
