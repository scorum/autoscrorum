import os
import tempfile
from contextlib import contextmanager
import secp256k1

def which(file):
    for path in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(path, file)):
            return os.path.join(path, file)


@contextmanager
def write_to_tempfile(content):
    with tempfile.NamedTemporaryFile() as file:
        with open(file.name, 'w') as f:
            f.write(content)
        yield file.name


def generate_key(passphrase):
    private_key = secp256k1.PrivateKey(bytes(passphrase.encode()))
    print(private_key.serialize())
    public_key = None
    result = (private_key, public_key)
    return result


def test_generator():
    generate_key('sjrpfhtnfhsjnvbimnbjkaiwnghfnfrw')
