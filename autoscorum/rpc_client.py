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
        return self._rpc.exec('get_accounts', [name])

    def get_info(self):
        result = self._rpc.exec("get_dynamic_global_properties", [])

        witness_schedule = self._rpc.exec("get_witness_schedule", [])
        result.update(witness_schedule)

        hardfork_version = self._rpc.exec("get_hardfork_version", [])
        result['hardfork_version'] = hardfork_version

        chain_properties = self._rpc.exec("get_chain_properties", [])
        result.update(chain_properties)

        reward_fund = self._rpc.exec("get_reward_fund", "post")
        result['post_reward_fund'] = reward_fund

        return result
