import time
import os
import tempfile
from contextlib import contextmanager

from datetime import datetime


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


def fmt_time_from_now(secs=0):
    time_format = '%Y-%m-%dT%H:%M:%S%Z'
    return datetime.utcfromtimestamp(time.time() + int(secs)).strftime(time_format)
