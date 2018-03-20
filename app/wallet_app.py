import argparse
import sys

import autoscorum.wallet as WalletImpl


def propmpt():
    print('>> ', end='', flush=True)


class CliApi:
    def CliApi(self, chain_id):
        self.impl = WalletImpl(chain_id)

    def update_witness(self, witness_name, url, block_signing_key, props):
        print(witness_name, url, block_signing_key, props)


class WalletApp:
    def __init__(self, chain_id):
        self.api = CliApi(chain_id)

    def help(self):
        pass

    def run(self):
        propmpt()

        for line in sys.stdin:
            if line == "exit\n":
                return 0

            words = line.split()

            if len(words) > 0:
                try:
                    getattr(self.api, words[0])(self.api, *words[1:])
                except AttributeError as e:
                    print("no such method in api error: \"%s\"" % e)
                except TypeError as e:
                    print(e)

            propmpt()


def main():
    parser = argparse.ArgumentParser(description='wallet app')

    parser.add_argument('--push', action="store", help='push transaction')
    parser.add_argument('--sign', action="store", help='sign transaction')
    parser.add_argument('--chain-id', action="store", help='chain id')
    parser.add_argument('--server-rpc-endpoint', action="store", help='chain id')

    args = parser.parse_args()
    options = vars(args)

    wallet = WalletApp(chain_id=options["chain_id"])

    return wallet.run()

