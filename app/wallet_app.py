import argparse
import sys

from autoscorum.wallet import Wallet


def propmpt():
    print('>> ', end='', flush=True)


class WalletApp:
    def __init__(self):
        self._run = True

    def help(self):
        pass

    def exit(self):
        self._run = False

    def save(self):
        pass

    def run(self, chain_id, server_rpc):
        propmpt()

        with Wallet(chain_id, server_rpc) as wallet:

            for line in sys.stdin:

                words = line.split()

                if len(words) > 0:

                    try:
                        getattr(self, words[0])(*words[1:])

                        if not self._run:
                            break

                        propmpt()
                        continue
                    except AttributeError:
                        pass
                    except TypeError:
                        pass

                    try:
                        print(words)
                        result = getattr(wallet, words[0])(*words[1:])
                        print(result)
                    except AttributeError as e:
                        print("no such method in api error: \"%s\"" % e)
                    except TypeError as e:
                        print(e)

                propmpt()

        self.save()
        return 0


def main():
    parser = argparse.ArgumentParser(description='wallet app')

    parser.add_argument('--chain-id', action="store", help='Chain ID to connect to')
    parser.add_argument('--server-rpc-endpoint', default="127.0.0.1:8090", action="store", help='Server websocket RPC endpoint')

    args = parser.parse_args()
    options = vars(args)

    wallet = WalletApp()

    return wallet.run(chain_id=options["chain_id"], server_rpc=options["server_rpc_endpoint"])
