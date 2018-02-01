import os
import tempfile
from contextlib import contextmanager
from steembase import account


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
    sha = hashlib.sha256(passphrase.encode())
    print(sha.hexdigest())
    private_key = secp256k1.PrivateKey(sha.hexdigest()[32:].encode())
    print(private_key.serialize())
    public_key = None
    result = (private_key, public_key)
    return result


def test_generator():
    generate_key('nitdelegate')
